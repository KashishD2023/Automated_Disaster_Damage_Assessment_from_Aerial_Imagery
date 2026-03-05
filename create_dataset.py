import os
import pandas as pd
import json
from PIL import Image

# --- CONFIGURATION ---
# Define directory paths for the dataset structure
BASE_DIR = "./data/santa_rosa_demo"
PRE_DIR = os.path.join(BASE_DIR, "pre")   # Directory containing pre-disaster images
POST_DIR = os.path.join(BASE_DIR, "post") # Directory containing post-disaster images
LABEL_DIR = os.path.join(BASE_DIR, "fema") # Directory containing label JSONs (ground truth)
OUTPUT_CSV = "./data/metadata.csv"        # Path where the validation report CSV will be saved


def validate_image(path):
    """Checks if an image can be opened and isn't corrupt."""
    # This ensures we don't crash later when trying to process a broken image file
    try:
        with Image.open(path) as img:
            img.verify()  # Verify file integrity (checks for truncation/corruption)
        return True
    except Exception:
        return False


def parse_json_label(path):
    """Opens the JSON to ensure it's readable and extracts a building count."""
    # This verifies the label file is valid JSON and contains the expected data structure
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Count how many building polygons are in this label file
            # xView2 structure: 'features' -> 'xy' -> 'properties' -> 'subtype'
            # We access 'xy' here to count pixel-coordinate polygons
            count = len(data['features']['xy'])
            return True, count
    except Exception:
        # Return False if JSON is malformed or keys are missing
        return False, 0


def main():
    records = []
    print(f"Scanning {BASE_DIR}...")

    # Iterate through the POST images (since they determine the damage label)
    # The post-disaster image is the primary key for our dataset pairs
    for filename in os.listdir(POST_DIR):
        if filename.endswith(".png"):
            # Construct IDs
            # File format: santa-rosa-wildfire_00000013_post_disaster.png
            # We strip the suffix to get the unique identifier (e.g., 'santa-rosa-wildfire_00000013')
            base_id = filename.replace("_post_disaster.png", "")

            # Define Expected Paths for all three components of a valid data point
            post_path = os.path.join(POST_DIR, filename)
            pre_path = os.path.join(PRE_DIR, f"{base_id}_pre_disaster.png")
            label_path = os.path.join(LABEL_DIR, f"{base_id}_post_disaster.json")

            # Initialize Status flags
            valid_pre = False
            valid_post = False
            valid_label = False
            building_count = 0

            # 1. Validate Post Image
            # Check existence AND file integrity
            if os.path.exists(post_path) and validate_image(post_path):
                valid_post = True

            # 2. Validate Pre Image
            # Check existence AND file integrity
            if os.path.exists(pre_path) and validate_image(pre_path):
                valid_pre = True

            # 3. Validate Label JSON
            # Check existence AND parse-ability
            if os.path.exists(label_path):
                is_valid_json, count = parse_json_label(label_path)
                if is_valid_json:
                    valid_label = True
                    building_count = count

            # Append metadata to records list
            # 'is_complete' is True only if ALL three components are valid
            records.append({
                "id": base_id,
                "disaster": base_id.split('_')[0], # Extract disaster name from ID
                "pre_path": pre_path,
                "post_path": post_path,
                "label_path": label_path,
                "building_count": building_count,
                "is_complete": (valid_pre and valid_post and valid_label)
            })

    # Create DataFrame from the records list
    df = pd.DataFrame(records)

    # Save to CSV for easy inspection/filtering later
    df.to_csv(OUTPUT_CSV, index=False)

    # --- REPORT ---
    # Print a summary of the dataset health to the console
    print("\n--- DATA VALIDATION REPORT ---")
    print(f"Total Rows Generated: {len(df)}")
    print(f"Complete/Valid Pairs: {df['is_complete'].sum()}")
    print(f"Corrupt/Missing Data: {len(df) - df['is_complete'].sum()}")
    print(f"Metadata saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()