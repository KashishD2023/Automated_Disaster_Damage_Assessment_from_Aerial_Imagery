import os
import glob
import json
from ai_damage_detector import DamageDetector
from shapely.wkt import loads
from shapely.geometry import mapping

# COLOR MAPPING
DAMAGE_COLOR = {
    "no-damage": "#00ff00",
    "minor-damage": "#ffff00",
    "major-damage": "#ffa500",
    "destroyed": "#ff0000",
    "un-classified": "#808080"
}


def process_all_images():
    """Process all images and create AI-predicted GeoJSON"""

    detector = DamageDetector()

    PRE_DIR = "./data/santa_rosa_demo/pre"
    POST_DIR = "./data/santa_rosa_demo/post"
    LABEL_DIR = "./data/santa_rosa_demo/fema"
    OUTPUT_FILE = "./data/ai_santa_rosa_damage.geojson"

    post_images = glob.glob(os.path.join(POST_DIR, "*_post_disaster.png"))

    print(f"Processing {len(post_images)} image pairs...\n")
    print("This will take a while (5-10 minutes)...\n")

    all_features = []
    total_buildings = 0

    for i, post_path in enumerate(post_images, 1):
        filename = os.path.basename(post_path)
        base_name = filename.replace("_post_disaster.png", "")
        pre_path = os.path.join(PRE_DIR, f"{base_name}_pre_disaster.png")
        label_path = os.path.join(LABEL_DIR, f"{base_name}_post_disaster.json")

        if not os.path.exists(pre_path):
            print(f"⚠️  [{i}/{len(post_images)}] Skipping {base_name} - no pre image")
            continue

        print(f"[{i}/{len(post_images)}] Processing {base_name}...")

        # Run AI analysis
        try:
            ai_predictions = detector.analyze_damage(pre_path, post_path)
            print(f"  AI found {len(ai_predictions)} buildings")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

        # Load ground truth labels for coordinate mapping
        if not os.path.exists(label_path):
            print(f"  ⚠️  No labels file, skipping")
            continue

        with open(label_path, 'r') as f:
            label_data = json.load(f)

        ground_truth_polygons = label_data['features']['lng_lat']

        # Map AI predictions to ground truth polygons
        # Assumption: Same order (this is a simplification)
        for j, ai_pred in enumerate(ai_predictions):
            if j >= len(ground_truth_polygons):
                break

            gt_polygon = ground_truth_polygons[j]
            wkt_str = gt_polygon['wkt']

            try:
                poly = loads(wkt_str)
                geometry = mapping(poly)

                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "damage": ai_pred['damage'],
                        "confidence": ai_pred.get('confidence', 0.0),
                        "description": ai_pred.get('description', ''),
                        "color": DAMAGE_COLOR.get(ai_pred['damage'], "#808080"),
                        "image_id": base_name,
                        "source": "ai_prediction"
                    }
                }
                all_features.append(feature)
                total_buildings += 1

            except Exception as e:
                continue

        print(f"  ✓ Mapped {min(len(ai_predictions), len(ground_truth_polygons))} buildings\n")

    # Create GeoJSON
    feature_collection = {
        "type": "FeatureCollection",
        "features": all_features
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(feature_collection, f, indent=2)

    print(f"\n✅ Complete!")
    print(f"Total buildings analyzed: {total_buildings}")
    print(f"AI predictions saved to: {OUTPUT_FILE}")

    # Print damage summary
    from collections import Counter
    damages = [f['properties']['damage'] for f in all_features]
    print(f"\nAI Damage Assessment Summary:")
    for damage_type, count in Counter(damages).most_common():
        pct = (count / total_buildings * 100) if total_buildings > 0 else 0
        print(f"  {damage_type}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    process_all_images()