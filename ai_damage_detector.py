"""
ai_damage_detector.py
=====================

Core AI classification module for disaster damage assessment.

ARCHITECTURE:
    This module does NOT detect buildings — building polygons come from
    pre-existing FEMA/xView2 label JSONs (stripped of damage labels).

    Instead, it:
    1. Reads building polygon locations from a stripped JSON label file
    2. Converts geographic coordinates (lng/lat) to pixel bounding boxes
    3. Sends the full pre/post satellite images to Google Gemini along with
       a text list of building pixel locations
    4. Gemini classifies each building's damage level by comparing pre vs post
    5. Returns results keyed by building UID for mapping back to polygons

USAGE:
    detector = DamageDetector()
    results = detector.analyze_tile(
        pre_image_path="./data/.../pre_disaster.png",
        post_image_path="./data/.../post_disaster.png",
        label_path="./data/.../post_disaster.json",  # stripped JSON (no damage labels)
        batch_size=85,
    )
    # results = [{"uid": "abc123", "damage": "destroyed", "confidence": 0.9, "description": "..."}, ...]

DEPENDENCIES:
    - google-genai (Google Gemini API client)
    - Pillow (PIL - image loading)
    - shapely (WKT polygon parsing)

ENVIRONMENT:
    Requires GOOGLE_API_KEY environment variable set with a valid Gemini API key.
"""

from google import genai
from google.genai import types
import json
import os
import io
import time
from PIL import Image


class DamageDetector:
    """
    Main class for AI-powered building damage classification.

    Uses Google Gemini vision model to compare pre/post disaster satellite
    images and classify building damage levels.
    """

    def __init__(self, api_key=None):
        """
        Initialize the detector with a Gemini API key.

        Args:
            api_key (str, optional): Google Gemini API key.
                If not provided, reads from GOOGLE_API_KEY environment variable.

        Raises:
            ValueError: If no API key is found.
        """
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("Please set GOOGLE_API_KEY environment variable")

        # Initialize the Google GenAI client
        self.client = genai.Client(api_key=api_key)

    def _call_gemini(self, contents, model='gemini-3-pro-preview', retries=5):
        """
        Low-level Gemini API call with automatic retry and rate limit handling.

        Handles:
            - 429 RESOURCE_EXHAUSTED errors by waiting the recommended retry delay
            - JSON parsing from model responses (strips markdown fences if present)
            - General errors with exponential backoff

        Args:
            contents (list): Content parts to send to Gemini (text + image parts).
            model (str): Gemini model identifier to use.
            retries (int): Maximum number of retry attempts for rate limit errors.

        Returns:
            dict or list: Parsed JSON response from the model.

        Raises:
            Exception: If all retry attempts are exhausted.
        """
        for attempt in range(retries + 1):
            try:
                # Make the API call to Gemini
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents
                )
                response_text = response.text

                # Parse JSON from response — Gemini sometimes wraps JSON in markdown code fences
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()

                return json.loads(json_str)

            except Exception as e:
                error_str = str(e)

                # === RATE LIMIT HANDLING ===
                # Google API returns 429 when you exceed request quotas.
                # The error includes a recommended retryDelay — we parse and respect it.
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = 40  # Default wait if we can't parse the delay
                    if "retryDelay" in error_str:
                        try:
                            import re
                            # Extract the number of seconds from retryDelay field
                            delay_match = re.search(r'retryDelay.*?(\d+)', error_str)
                            if delay_match:
                                wait_time = int(delay_match.group(1)) + 5  # Add 5s buffer
                        except:
                            pass

                    print(f"    Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{retries + 1})...")
                    time.sleep(wait_time)
                    continue  # Retry the same request

                # === GENERAL ERROR HANDLING ===
                print(f"    Attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    time.sleep(2)  # Brief pause before retry
                else:
                    raise  # All retries exhausted, propagate the error

    def classify_batch(self, pre_image_bytes, post_image_bytes, buildings_info, model='gemini-3-pro-preview'):
        """
        Classify a batch of buildings in a single API call.

        Sends the FULL pre and post disaster images along with a text prompt
        listing each building's pixel bounding box coordinates. The model
        examines each location in both images and returns damage classifications.

        This approach is more efficient than sending individual crops because:
        - Only 2 images per API call regardless of building count
        - Model can see surrounding context for better classification
        - Reduces total number of API calls (important for rate limits)

        Args:
            pre_image_bytes (bytes): Full pre-disaster image as PNG bytes.
            post_image_bytes (bytes): Full post-disaster image as PNG bytes.
            buildings_info (list): List of dicts with keys:
                - "uid" (str): Unique building identifier
                - "x1", "y1", "x2", "y2" (int): Pixel bounding box coordinates
            model (str): Gemini model to use for classification.

        Returns:
            list: Dicts with "uid", "damage", "confidence", "description" for each building.
        """

        # Build a human-readable list of building locations for the prompt
        building_list = ""
        for b in buildings_info:
            building_list += f'  - UID: {b["uid"]}, Location: pixel bbox [{b["x1"]},{b["y1"]} to {b["x2"]},{b["y2"]}]\n'

        # === CLASSIFICATION PROMPT ===
        # Key design decisions:
        # - Only 3 damage levels (no "major-damage") to match xView2 ground truth labels
        # - Explicit instruction to examine each building individually
        # - Pixel coordinates tell the model exactly where to look in the image
        prompt = f"""You are an expert satellite imagery disaster damage assessor.

I'm showing you two satellite images of the same area:
1. FIRST IMAGE: PRE-DISASTER (before the event)  
2. SECOND IMAGE: POST-DISASTER (after the event)

There are {len(buildings_info)} buildings in this image that I need you to classify. 
Each building's location is given as a pixel bounding box [x1,y1 to x2,y2] where (0,0) is the top-left corner.

Buildings to classify:
{building_list}

For EACH building, compare its appearance in the pre vs post image at the given pixel location and classify as:
- "no-damage": Building looks the same, roof intact, structure unchanged
- "minor-damage": Small changes visible but building is structurally intact  
- "destroyed": Building is gone, reduced to rubble/ash/foundation only

You MUST use ONLY these three labels. Do NOT use "major-damage" or any other label.

CRITICAL RULES:
- Look at EACH building individually at its specific pixel location
- Not all buildings will have the same damage - examine each one carefully
- If a building has green trees and intact roof in the post image, it is "no-damage"
- If a building is clearly reduced to rubble/gray ash, it is "destroyed"
- Provide your honest best assessment for each

Return ONLY a JSON array (no markdown, no explanation):
[
  {{"uid": "abc123", "damage": "destroyed", "confidence": 0.9, "description": "Reduced to ash"}},
  {{"uid": "def456", "damage": "no-damage", "confidence": 0.85, "description": "Roof and structure intact"}}
]"""

        # Assemble the API request: pre image, post image, then the classification prompt
        contents = [
            "PRE-DISASTER IMAGE:",
            types.Part.from_bytes(data=pre_image_bytes, mime_type='image/png'),
            "POST-DISASTER IMAGE:",
            types.Part.from_bytes(data=post_image_bytes, mime_type='image/png'),
            prompt
        ]

        return self._call_gemini(contents, model=model)

    def analyze_tile(self, pre_image_path, post_image_path, label_path, batch_size=85, model='gemini-3-pro-preview',
                     progress_callback=None):
        """
        Full analysis pipeline for a single satellite image tile.

        This is the main entry point. It orchestrates the entire flow:
        1. Load the stripped label JSON (building polygons, no damage labels)
        2. Parse WKT polygon geometries and extract lng/lat coordinates
        3. Estimate the tile's geographic bounds from polygon extent
        4. Convert each polygon's lng/lat coords to pixel bounding boxes
        5. Send buildings to Gemini in batches for classification
        6. Return classified results keyed by UID

        Args:
            pre_image_path (str): Path to the pre-disaster satellite image (PNG).
            post_image_path (str): Path to the post-disaster satellite image (PNG).
            label_path (str): Path to the stripped FEMA label JSON (polygons only).
            batch_size (int): Number of buildings per API call. Higher = fewer calls
                but longer prompts. 85 is a good default for Gemini Pro.
            model (str): Gemini model identifier.
            progress_callback (callable, optional): Function(batch_num, total_batches)
                called after each batch for progress reporting.

        Returns:
            list: Dicts with keys:
                - "uid" (str): Building unique ID (matches the label JSON)
                - "damage" (str): One of "no-damage", "minor-damage", "destroyed", "un-classified"
                - "confidence" (float): 0.0-1.0 confidence score
                - "description" (str): Brief text description of observed damage
        """
        from shapely.wkt import loads as wkt_loads

        # =====================================================================
        # STEP 1: Load the stripped label JSON
        # =====================================================================
        # The label file contains building polygons as WKT strings with UIDs
        # but NO damage classifications (those were stripped by strip_damage_labels.py)
        with open(label_path, 'r') as f:
            label_data = json.load(f)

        polygons = label_data.get('features', {}).get('lng_lat', [])
        if not polygons:
            print("  No polygons found in label file")
            return []

        # =====================================================================
        # STEP 2: Load the satellite images
        # =====================================================================
        pre_img = Image.open(pre_image_path)
        post_img = Image.open(post_image_path)
        img_w, img_h = pre_img.size  # Typically 1024x1024 for xView2 tiles
        print(f"  Image size: {img_w}x{img_h}")

        # Convert images to PNG bytes for the Gemini API
        pre_buf = io.BytesIO()
        pre_img.save(pre_buf, format='PNG')
        pre_bytes = pre_buf.getvalue()

        post_buf = io.BytesIO()
        post_img.save(post_buf, format='PNG')
        post_bytes = post_buf.getvalue()

        # =====================================================================
        # STEP 3: Parse all polygon geometries
        # =====================================================================
        # Each polygon is a WKT string like:
        #   POLYGON ((-122.746 38.501, -122.747 38.502, ...))
        # We parse these into shapely geometry objects and collect all coordinates
        # to determine the geographic extent of this tile.
        all_lngs = []
        all_lats = []
        parsed_polygons = []

        for poly_data in polygons:
            wkt_str = poly_data.get('wkt', '')
            uid = poly_data.get('properties', {}).get('uid', 'unknown')
            try:
                geom = wkt_loads(wkt_str)
                coords = list(geom.exterior.coords)
                lngs = [c[0] for c in coords]  # Longitude (x-axis)
                lats = [c[1] for c in coords]  # Latitude (y-axis)
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

        # =====================================================================
        # STEP 4: Estimate tile geographic bounds
        # =====================================================================
        # IMPORTANT: The building polygons don't cover the entire image tile.
        # The image extends beyond the polygon coverage (roads, open space, etc.)
        # We approximate the full tile bounds by adding a 10% margin around
        # the polygon extent. This isn't perfect but works reasonably well.
        #
        # NOTE: This is the main source of polygon-to-pixel alignment error.
        # If the xView2 data included pixel coordinates (xy) alongside lng_lat,
        # we could skip this estimation entirely.
        min_lng, max_lng = min(all_lngs), max(all_lngs)
        min_lat, max_lat = min(all_lats), max(all_lats)

        lng_range = max_lng - min_lng
        lat_range = max_lat - min_lat

        # Add 10% margin on each side to approximate full tile bounds
        margin = 0.10
        min_lng -= lng_range * margin
        max_lng += lng_range * margin
        min_lat -= lat_range * margin
        max_lat += lat_range * margin
        lng_range = max_lng - min_lng
        lat_range = max_lat - min_lat

        print(f"  Tile bounds: lng [{min_lng:.6f}, {max_lng:.6f}], lat [{min_lat:.6f}, {max_lat:.6f}]")
        print(f"  {len(parsed_polygons)} buildings to classify")

        # =====================================================================
        # STEP 5: Convert each polygon to a pixel bounding box
        # =====================================================================
        # For each building polygon, we convert its lng/lat vertices to pixel
        # coordinates using linear interpolation within the estimated tile bounds.
        #
        # Geographic to pixel mapping:
        #   pixel_x = (longitude - min_lng) / lng_range * image_width
        #   pixel_y = (max_lat - latitude) / lat_range * image_height
        #
        # Note: Latitude is inverted because geographic north (higher lat) maps
        # to the top of the image (lower pixel y), while images count y from top.
        buildings_with_bbox = []
        for poly_info in parsed_polygons:
            px_coords = []
            for lng, lat in zip(poly_info['lngs'], poly_info['lats']):
                px_x = (lng - min_lng) / lng_range * img_w
                px_y = (max_lat - lat) / lat_range * img_h  # Inverted: north = top = low y
                px_coords.append((px_x, px_y))

            # Compute axis-aligned bounding box from pixel coordinates
            xs = [c[0] for c in px_coords]
            ys = [c[1] for c in px_coords]
            x1 = max(0, int(min(xs)))
            y1 = max(0, int(min(ys)))
            x2 = min(img_w, int(max(xs)))
            y2 = min(img_h, int(max(ys)))

            # Filter out tiny bounding boxes (likely noise or degenerate polygons)
            if (x2 - x1) < 5 or (y2 - y1) < 5:
                print(f"  Skipping tiny building {poly_info['uid'][:8]}: {x2 - x1}x{y2 - y1}px")
                continue

            buildings_with_bbox.append({
                'uid': poly_info['uid'],
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            })

        print(f"  {len(buildings_with_bbox)} buildings with valid bboxes")

        # =====================================================================
        # STEP 6: Classify buildings in batches via Gemini API
        # =====================================================================
        # We send the full pre+post images with each batch, along with a text
        # list of building bounding boxes. The model examines each location
        # and returns a damage classification per building.
        #
        # Batching is necessary because:
        # - API rate limits (especially on free/preview tiers)
        # - Very long prompts with 170+ buildings might degrade quality
        # - Allows progress reporting between batches
        all_results = []
        total_batches = (len(buildings_with_bbox) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(buildings_with_bbox), batch_size):
            batch_end = min(batch_idx + batch_size, len(buildings_with_bbox))
            batch_num = batch_idx // batch_size + 1
            batch_buildings = buildings_with_bbox[batch_idx:batch_end]

            print(f"  Batch {batch_num}/{total_batches}: {len(batch_buildings)} buildings...")

            # Report progress if callback provided (used by Streamlit progress bar)
            if progress_callback:
                progress_callback(batch_num, total_batches)

            try:
                batch_results = self.classify_batch(pre_bytes, post_bytes, batch_buildings, model=model)

                # === RESULT VALIDATION ===
                # The AI might reorder results, skip buildings, or return extra entries.
                # We match results back to buildings by UID, falling back to index order.
                if isinstance(batch_results, list):
                    # Build a UID lookup from the AI's response
                    result_by_uid = {r.get('uid', ''): r for r in batch_results}

                    for b in batch_buildings:
                        uid = b['uid']
                        if uid in result_by_uid:
                            # Found by UID match — best case
                            result = result_by_uid[uid]
                            result['uid'] = uid
                            all_results.append(result)
                        else:
                            # UID not found — try matching by index position
                            idx = batch_buildings.index(b)
                            if idx < len(batch_results):
                                result = batch_results[idx]
                                result['uid'] = uid
                                all_results.append(result)
                            else:
                                # AI completely missed this building
                                all_results.append({
                                    'uid': uid,
                                    'damage': 'un-classified',
                                    'confidence': 0.0,
                                    'description': 'AI did not return result for this building'
                                })

                    # Log damage distribution for this batch
                    damages = [r.get('damage', '?') for r in batch_results]
                    print(f"    Results: {dict((d, damages.count(d)) for d in set(damages))}")
                else:
                    # Response wasn't a list — something went wrong
                    print(f"    Unexpected response type: {type(batch_results)}")
                    for b in batch_buildings:
                        all_results.append({
                            'uid': b['uid'],
                            'damage': 'un-classified',
                            'confidence': 0.0,
                            'description': 'Unexpected API response format'
                        })

            except Exception as e:
                # Batch failed entirely — mark all buildings as un-classified
                print(f"    Batch {batch_num} failed: {e}")
                for b in batch_buildings:
                    all_results.append({
                        'uid': b['uid'],
                        'damage': 'un-classified',
                        'confidence': 0.0,
                        'description': f'Error: {e}'
                    })

            # === RATE LIMITING ===
            # Pause between batches to avoid hitting Google API quotas.
            # Gemini Pro preview has stricter limits than Flash.
            # 10s between batches keeps us well under the limit.
            if batch_num < total_batches:
                wait = 10
                print(f"    Waiting {wait}s before next batch...")
                time.sleep(wait)

        # =====================================================================
        # STEP 7: Summary and return
        # =====================================================================
        print(f"\n  Classification complete: {len(all_results)} buildings")
        damage_summary = {}
        for r in all_results:
            d = r.get('damage', 'unknown')
            damage_summary[d] = damage_summary.get(d, 0) + 1
        print(f"  Summary: {damage_summary}")

        return all_results


# =============================================================================
# STANDALONE TEST
# =============================================================================
# Run this file directly to test classification on a single tile:
#   python ai_damage_detector.py
#
# Make sure GOOGLE_API_KEY is set and the data directory exists.

def main():
    """Test with a single tile."""
    detector = DamageDetector()

    # Example tile paths — adjust these to match your data
    pre_image = "./data/santa_rosa_demo/pre/santa-rosa-wildfire_00000012_pre_disaster.png"
    post_image = "./data/santa_rosa_demo/post/santa-rosa-wildfire_00000012_post_disaster.png"
    label_file = "./data/santa_rosa_demo/fema/santa-rosa-wildfire_00000012_post_disaster.json"

    print("Analyzing tile...\n")
    results = detector.analyze_tile(pre_image, post_image, label_file, batch_size=15)

    print(f"\nResults: {len(results)} buildings classified")
    from collections import Counter
    damages = Counter(r['damage'] for r in results)
    for d, c in damages.most_common():
        print(f"  {d}: {c}")

    # Save results to JSON for inspection
    with open("./data/ai_test_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved to ./data/ai_test_results.json")


if __name__ == "__main__":
    main()