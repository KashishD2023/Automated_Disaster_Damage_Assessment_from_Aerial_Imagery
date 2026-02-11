import json
import os
import glob
from shapely.wkt import loads
from shapely.geometry import mapping
import geojson

# --- CONFIGURATION ---
INPUT_DIR = "./data/guatemala_demo/fema"
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

        # USE lng_lat INSTEAD OF xy !!!
        for obj in data['features']['lng_lat']:  # <--- CHANGED THIS LINE
            wkt_str = obj['wkt']
            try:
                poly = loads(wkt_str)
                geometry = mapping(poly)
            except Exception as e:
                print(f"Skipping invalid polygon: {e}")
                continue

            subtype = obj['properties'].get('subtype', 'un-classified')

            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "damage": subtype,
                    "color": DAMAGE_COLOR.get(subtype, "#808080"),
                    "image_id": data['metadata']['img_name']
                }
            }
            features.append(feature)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_file, 'w') as f:
        json.dump(feature_collection, f, indent=2)

    print(f"Success! Created {len(features)} features")
    print(f"Map data saved to {output_file}")

    # Print first coordinate to verify
    if features:
        first_coord = features[0]['geometry']['coordinates'][0][0]
        print(f"Sample coordinate: {first_coord} (should be around -90.8, 14.4)")


if __name__ == "__main__":
    xview2_to_geojson(INPUT_DIR, OUTPUT_FILE)