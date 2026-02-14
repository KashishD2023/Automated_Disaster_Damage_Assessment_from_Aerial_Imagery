import json
import os
import glob
from shapely.wkt import loads
from shapely.geometry import mapping
import geojson

# --- CONFIGURATION ---
# Define input/output paths for the Santa Rosa dataset
INPUT_DIR = "./data/santa_rosa_demo/fema"  # CHANGED
OUTPUT_FILE = "./data/santa_rosa_damage.geojson"  # CHANGED

# COLOR MAPPING
# Map damage classification strings to specific hex colors for visualization
DAMAGE_COLOR = {
    "no-damage": "#00ff00",      # Green
    "minor-damage": "#ffff00",   # Yellow
    "major-damage": "#ffa500",   # Orange
    "destroyed": "#ff0000",      # Red
    "un-classified": "#808080"   # Grey
}

def xview2_to_geojson(input_dir, output_file):
    """
    Converts xView2 dataset labels (JSON) into a single GeoJSON file
    suitable for mapping software (QGIS, Mapbox, etc.).
    """
    features = []

    # Validation: Ensure the input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory not found: {input_dir}")
        return

    # Find all JSON label files in the directory
    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    print(f"Found {len(json_files)} label files in {input_dir}...")

    # Process each label file
    for j_file in json_files:
        with open(j_file, 'r') as f:
            data = json.load(f)

        # Filter: Only process 'post-disaster' files as they contain the damage labels
        if "post" not in j_file:
            continue

        # USE lng_lat INSTEAD OF xy !!!
        # The dataset contains both pixel coordinates ('xy') and geographical coordinates ('lng_lat').
        # We access 'lng_lat' to map the polygons to real-world locations.
        for obj in data['features']['lng_lat']:  # <--- CHANGED THIS LINE
            wkt_str = obj['wkt']
            try:
                # Convert WKT (Well-Known Text) string to a Shapely geometry object
                poly = loads(wkt_str)
                # Convert Shapely object to GeoJSON geometry format
                geometry = mapping(poly)
            except Exception as e:
                print(f"Skipping invalid polygon: {e}")
                continue

            # Extract the damage type (e.g., 'destroyed', 'minor-damage')
            subtype = obj['properties'].get('subtype', 'un-classified')

            # Create the GeoJSON Feature object
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "damage": subtype,
                    "color": DAMAGE_COLOR.get(subtype, "#808080"), # Assign color based on damage
                    "image_id": data['metadata']['img_name']       # Track source image
                }
            }
            features.append(feature)

    # bundle all features into a FeatureCollection
    feature_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    # Write the final GeoJSON to disk
    with open(output_file, 'w') as f:
        json.dump(feature_collection, f, indent=2)

    print(f"Success! Created {len(features)} features")
    print(f"Map data saved to {output_file}")

    # Print first coordinate to verify
    # Sanity check: Ensure coordinates look like Lat/Long (e.g., -90.8) and not pixels (e.g., 1024)
    if features:
        first_coord = features[0]['geometry']['coordinates'][0][0]
        print(f"Sample coordinate: {first_coord} (should be around -90.8, 14.4)")


if __name__ == "__main__":
    xview2_to_geojson(INPUT_DIR, OUTPUT_FILE)