import json
import os
import glob
from shapely.wkt import loads
import geojson

# --- CONFIGURATION (This is what you asked about) ---
INPUT_DIR = "./data/guatemala_demo/fema"  # <--- HERE IT IS
OUTPUT_FILE = "./data/guatemala_damage.geojson"

# COLOR MAPPING
DAMAGE_COLOR = {
    "no-damage": "#00ff00",  # Green
    "minor-damage": "#ffff00",  # Yellow
    "major-damage": "#ffa500",  # Orange
    "destroyed": "#ff0000",  # Red
    "un-classified": "#808080"  # Grey
}


def xview2_to_geojson(input_dir, output_file):
    features = []

    # Verify directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory not found: {input_dir}")
        return

    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    print(f"Found {len(json_files)} label files in {input_dir}...")

    for j_file in json_files:
        with open(j_file, 'r') as f:
            data = json.load(f)

        if "post" not in j_file:
            continue

        for obj in data['features']['xy']:
            wkt_str = obj['wkt']
            try:
                poly = loads(wkt_str)
            except Exception:
                continue

            subtype = obj['properties'].get('subtype', 'un-classified')

            feature = geojson.Feature(
                geometry=poly,
                properties={
                    "damage": subtype,
                    "color": DAMAGE_COLOR.get(subtype, "#808080"),
                    "image_id": data['metadata']['img_name']
                }
            )
            features.append(feature)

    feature_collection = geojson.FeatureCollection(features)
    with open(output_file, 'w') as f:
        geojson.dump(feature_collection, f)

    print(f"Success! Map data saved to {output_file}")


if __name__ == "__main__":
    xview2_to_geojson(INPUT_DIR, OUTPUT_FILE)