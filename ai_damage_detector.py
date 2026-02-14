from google import genai
from google.genai import types
import json
import os
import io
from PIL import Image


class DamageDetector:

    def __init__(self, api_key=None):
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("Please set GOOGLE_API_KEY environment variable")

        self.client = genai.Client(api_key=api_key)

    def classify_building(self, pre_crop_bytes, post_crop_bytes):
        """
        Classify damage for a single building given cropped pre/post images.
        Returns: {"damage": "...", "confidence": 0.0-1.0, "description": "..."}
        """

        prompt = """You are an expert disaster damage assessor. You are looking at two cropped satellite images of the SAME building:
1. FIRST IMAGE: PRE-DISASTER (before)
2. SECOND IMAGE: POST-DISASTER (after)

Compare the two images and classify the building's damage level as exactly ONE of:
- "no-damage": Building appears identical, roof and structure intact
- "minor-damage": Minor cosmetic changes, building still standing and structurally sound
- "major-damage": Significant structural damage, roof/walls partially collapsed or burned
- "destroyed": Building completely collapsed, just rubble/ash, or foundation only remains

Return ONLY a JSON object (no markdown, no extra text):
{"damage": "destroyed", "confidence": 0.85, "description": "Roof gone, only foundation visible"}
"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    "PRE-DISASTER (before):",
                    types.Part.from_bytes(data=pre_crop_bytes, mime_type='image/png'),
                    "POST-DISASTER (after):",
                    types.Part.from_bytes(data=post_crop_bytes, mime_type='image/png'),
                    prompt
                ]
            )

            response_text = response.text

            # Parse JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            result = json.loads(json_str)
            return result

        except Exception as e:
            print(f"    Error classifying building: {e}")
            return {"damage": "un-classified", "confidence": 0.0, "description": f"Error: {e}"}

    def classify_buildings_batch(self, pre_crop_bytes_list, post_crop_bytes_list, uids):
        """
        Classify multiple buildings in a single API call for efficiency.
        Sends all crops at once with numbered labels.
        Returns: list of {"uid": "...", "damage": "...", "confidence": 0.0-1.0, "description": "..."}
        """

        # Build content with numbered building pairs
        contents = []
        for i, (pre_bytes, post_bytes, uid) in enumerate(zip(pre_crop_bytes_list, post_crop_bytes_list, uids)):
            contents.append(f"BUILDING {i+1} (uid: {uid}) - PRE:")
            contents.append(types.Part.from_bytes(data=pre_bytes, mime_type='image/png'))
            contents.append(f"BUILDING {i+1} (uid: {uid}) - POST:")
            contents.append(types.Part.from_bytes(data=post_bytes, mime_type='image/png'))

        prompt = f"""You are an expert disaster damage assessor analyzing {len(uids)} buildings.
For each building, you see a PRE-DISASTER and POST-DISASTER satellite image crop.

Classify each building's damage as exactly ONE of:
- "no-damage": Building appears identical, roof and structure intact
- "minor-damage": Minor cosmetic changes, still standing
- "major-damage": Significant structural damage, roof/walls partially collapsed
- "destroyed": Completely collapsed, rubble/ash, foundation only

IMPORTANT: Look carefully at each building individually. Not all buildings will have the same damage level.
Buildings with intact roofs and green surroundings in the post image are likely "no-damage".
Buildings reduced to gray rubble or ash are likely "destroyed".

Return ONLY a JSON array (no markdown):
[
  {{"uid": "...", "damage": "no-damage", "confidence": 0.9, "description": "Roof intact"}},
  {{"uid": "...", "damage": "destroyed", "confidence": 0.95, "description": "Only foundation remains"}}
]
"""
        contents.append(prompt)

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents
            )

            response_text = response.text

            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            results = json.loads(json_str)
            return results

        except Exception as e:
            print(f"  Error in batch classification: {e}")
            return [{"uid": uid, "damage": "un-classified", "confidence": 0.0, "description": f"Error: {e}"} for uid in uids]

    def analyze_tile(self, pre_image_path, post_image_path, label_path, batch_size=10, progress_callback=None):
        """
        Full pipeline for one tile:
        1. Load stripped JSON (polygons only)
        2. Convert lng_lat polygons to pixel bounding boxes
        3. Crop each building from pre+post images
        4. Send to Gemini in batches for classification
        5. Return results with UIDs for mapping back to polygons

        Returns: list of {"uid": "...", "damage": "...", "confidence": ..., "description": "..."}
        """
        from shapely.wkt import loads as wkt_loads

        # Load label data
        with open(label_path, 'r') as f:
            label_data = json.load(f)

        polygons = label_data.get('features', {}).get('lng_lat', [])
        if not polygons:
            print("  No polygons found in label file")
            return []

        # Load images
        pre_img = Image.open(pre_image_path)
        post_img = Image.open(post_image_path)
        img_w, img_h = pre_img.size  # typically 1024x1024

        # Compute tile geo-bounds from all polygon coordinates
        all_lngs = []
        all_lats = []
        parsed_polygons = []

        for poly_data in polygons:
            wkt_str = poly_data.get('wkt', '')
            uid = poly_data.get('properties', {}).get('uid', 'unknown')
            try:
                geom = wkt_loads(wkt_str)
                coords = list(geom.exterior.coords)
                lngs = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                all_lngs.extend(lngs)
                all_lats.extend(lats)
                parsed_polygons.append({
                    'uid': uid,
                    'geom': geom,
                    'lngs': lngs,
                    'lats': lats,
                })
            except Exception as e:
                print(f"  Skipping invalid polygon {uid}: {e}")
                continue

        if not parsed_polygons:
            return []

        # Tile geo-bounds (min/max of all polygons)
        min_lng, max_lng = min(all_lngs), max(all_lngs)
        min_lat, max_lat = min(all_lats), max(all_lats)

        # Add small buffer to avoid edge clipping
        lng_range = max_lng - min_lng
        lat_range = max_lat - min_lat
        min_lng -= lng_range * 0.02
        max_lng += lng_range * 0.02
        min_lat -= lat_range * 0.02
        max_lat += lat_range * 0.02
        lng_range = max_lng - min_lng
        lat_range = max_lat - min_lat

        print(f"  Tile bounds: lng [{min_lng:.6f}, {max_lng:.6f}], lat [{min_lat:.6f}, {max_lat:.6f}]")
        print(f"  {len(parsed_polygons)} buildings to classify")

        # Convert each polygon to pixel bbox and crop
        crops_pre = []
        crops_post = []
        crop_uids = []
        crop_metadata = []

        PADDING = 15  # pixels padding around building crop

        for poly_info in parsed_polygons:
            # Convert lng/lat to pixel coords
            px_coords = []
            for lng, lat in zip(poly_info['lngs'], poly_info['lats']):
                px_x = int((lng - min_lng) / lng_range * img_w)
                px_y = int((max_lat - lat) / lat_range * img_h)  # lat is inverted
                px_coords.append((px_x, px_y))

            # Bounding box in pixels
            xs = [c[0] for c in px_coords]
            ys = [c[1] for c in px_coords]
            x1 = max(0, min(xs) - PADDING)
            y1 = max(0, min(ys) - PADDING)
            x2 = min(img_w, max(xs) + PADDING)
            y2 = min(img_h, max(ys) + PADDING)

            # Skip tiny crops (probably noise)
            if (x2 - x1) < 10 or (y2 - y1) < 10:
                continue

            # Crop pre and post
            pre_crop = pre_img.crop((x1, y1, x2, y2))
            post_crop = post_img.crop((x1, y1, x2, y2))

            # Convert to bytes
            pre_buf = io.BytesIO()
            pre_crop.save(pre_buf, format='PNG')
            pre_bytes = pre_buf.getvalue()

            post_buf = io.BytesIO()
            post_crop.save(post_buf, format='PNG')
            post_bytes = post_buf.getvalue()

            crops_pre.append(pre_bytes)
            crops_post.append(post_bytes)
            crop_uids.append(poly_info['uid'])

        print(f"  Cropped {len(crop_uids)} buildings, sending to AI in batches of {batch_size}...")

        # Classify in batches
        all_results = []
        total_batches = (len(crop_uids) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(crop_uids), batch_size):
            batch_end = min(batch_idx + batch_size, len(crop_uids))
            batch_num = batch_idx // batch_size + 1

            batch_pre = crops_pre[batch_idx:batch_end]
            batch_post = crops_post[batch_idx:batch_end]
            batch_uids = crop_uids[batch_idx:batch_end]

            print(f"  Batch {batch_num}/{total_batches}: buildings {batch_idx+1}-{batch_end}")

            if progress_callback:
                progress_callback(batch_num, total_batches)

            results = self.classify_buildings_batch(batch_pre, batch_post, batch_uids)
            all_results.extend(results)

        # Ensure UIDs are set correctly (in case AI response didn't include them)
        for i, result in enumerate(all_results):
            if i < len(crop_uids):
                result['uid'] = crop_uids[i]

        return all_results


def main():
    """Test with a single tile"""
    detector = DamageDetector()

    pre_image = "./data/santa_rosa_demo/pre/santa-rosa-wildfire_00000012_pre_disaster.png"
    post_image = "./data/santa_rosa_demo/post/santa-rosa-wildfire_00000012_post_disaster.png"
    label_file = "./data/santa_rosa_demo/fema/santa-rosa-wildfire_00000012_post_disaster.json"

    print(f"Analyzing tile...")
    results = detector.analyze_tile(pre_image, post_image, label_file, batch_size=10)

    print(f"\nResults: {len(results)} buildings classified")
    from collections import Counter
    damages = Counter(r['damage'] for r in results)
    for d, c in damages.most_common():
        print(f"  {d}: {c}")

    with open("./data/ai_test_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved to ./data/ai_test_results.json")


if __name__ == "__main__":
    main()