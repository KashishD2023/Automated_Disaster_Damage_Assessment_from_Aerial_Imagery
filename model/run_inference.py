import pandas as pd
import json
import random
from datetime import datetime

# file paths
CSV_INPUT = '../frontend/public/demo_images/tiles_demo.csv'
GEOJSON_OUTPUT = 'predictions_demo.geojson'

# FEMA damage classifications 
FEMA_CLASSES = ["NO DAMAGE", "MINOR", "MAJOR", "DESTROYED"]

def run_mock_inference():
    try:
        # reads demo file 
        df = pd.read_csv(CSV_INPUT)
    except FileNotFoundError:
        print(f"Error: {CSV_INPUT} not found. Ensure correct file path.")
        return

    prediction_features = []

    # processes each tile
    for _, row in df.iterrows():
        tile_id = row['tile_id']

        # placeholder for actual classification when talking to VLM api
        predicted_class = random.choice(FEMA_CLASSES)
        confidence = round(random.uniform(0.65, 0.98), 2)

        # data for the dashboard and evaluation
        # some data below are placeholders
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[ # placeholder
                    [-95.36, 29.76], [-95.35, 29.76], 
                    [-95.35, 29.75], [-95.36, 29.75], [-95.36, 29.76]
                ]]
            },
            "properties": {
                "tile_id": tile_id,
                "damage_class": predicted_class,
                "confidence": confidence,
                "explanation": f"Model identified {predicted_class} based on structural variance.", # placeholder: maybe be more descriptive?
                "timestamp": datetime.now().isoformat()
            }
        }

        prediction_features.append(feature)


    # export standardized GeoJSON 
    output_data = {
        "type": "FeatureCollection",
        "features": prediction_features
    }

    with open(GEOJSON_OUTPUT, 'w') as f:
        json.dump(output_data, f, indent=4)
    
    print(f"Success: {GEOJSON_OUTPUT} created for the Week 2 Demo.") # placeholder message for 


run_mock_inference()
