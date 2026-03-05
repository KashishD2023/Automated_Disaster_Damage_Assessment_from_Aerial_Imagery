import os
import json
import glob
import copy

# --- CONFIGURATION ---
# FEMA_DIR will eventually contain the "unlabeled" files (questions)
# GROUND_TRUTH_DIR will contain the original files with damage labels (answers)
FEMA_DIR = "./data/santa_rosa_demo/fema"
GROUND_TRUTH_DIR = "./data/santa_rosa_demo/ground_truth"


def strip_labels():
    # Create the directory to store the "Answer Key" if it doesn't exist
    os.makedirs(GROUND_TRUTH_DIR, exist_ok=True)

    # Find all JSON label files in the source directory
    label_files = glob.glob(os.path.join(FEMA_DIR, "*.json"))

    if not label_files:
        print(f"⚠️  No JSON files found in {FEMA_DIR}")
        return

    print(f"Processing {len(label_files)} label files...\n")

    total_buildings = 0
    damage_counts = {}

    for label_path in sorted(label_files):
        filename = os.path.basename(label_path)

        with open(label_path, 'r') as f:
            data = json.load(f)

        # --- 1. Save ground truth (exact copy) ---
        # Before we modify anything, save the original file with damage labels
        # to the ground_truth folder. This is our "Answer Key" for validation later.
        gt_path = os.path.join(GROUND_TRUTH_DIR, filename)
        with open(gt_path, 'w') as f:
            json.dump(data, f, indent=2)

        # --- 2. Create stripped version ---
        # Create a deep copy so we can modify 'stripped' without affecting 'data'
        stripped = copy.deepcopy(data)

        # Strip damage from lng_lat features (Geographic coordinates)
        if 'features' in stripped and 'lng_lat' in stripped['features']:
            for polygon in stripped['features']['lng_lat']:
                # Track original damage for stats before deleting it
                # We want to know the distribution of the original dataset
                original_damage = polygon.get('properties', {}).get('subtype', 'unknown')
                damage_counts[original_damage] = damage_counts.get(original_damage, 0) + 1
                total_buildings += 1

                # Remove damage classification fields ('subtype')
                # This simulates "unseen" data where we know WHERE the building is,
                # but not WHAT the damage is.
                if 'properties' in polygon:
                    polygon['properties'].pop('subtype', None)     # The damage label
                    polygon['properties'].pop('feature_type', None)

        # Strip damage from xy features too (Pixel coordinates)
        # We must clean both coordinate systems to ensure no labels leak through
        if 'features' in stripped and 'xy' in stripped['features']:
            for polygon in stripped['features']['xy']:
                if 'properties' in polygon:
                    polygon['properties'].pop('subtype', None)
                    polygon['properties'].pop('feature_type', None)

        # Overwrite the original file in FEMA_DIR with the stripped version
        # Now FEMA_DIR contains only the "Questions" (geometry only),
        # and GROUND_TRUTH_DIR contains the "Answers" (geometry + damage).
        stripped_path = os.path.join(FEMA_DIR, filename)
        with open(stripped_path, 'w') as f:
            json.dump(stripped, f, indent=2)

        n_buildings = len(stripped.get('features', {}).get('lng_lat', []))
        print(f"  ✓ {filename}: {n_buildings} buildings stripped")

    # --- REPORT ---
    print(f"\n{'=' * 50}")
    print(f"✅ Complete!")
    print(f"Total buildings: {total_buildings}")
    print(f"Stripped files (overwritten): {FEMA_DIR}/")
    print(f"Ground truth backup:          {GROUND_TRUTH_DIR}/")
    print(f"\nOriginal damage distribution (ground truth):")
    # Sort by count descending to show most common damage types first
    for damage_type, count in sorted(damage_counts.items(), key=lambda x: -x[1]):
        pct = count / total_buildings * 100 if total_buildings > 0 else 0
        print(f"  {damage_type}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    strip_labels()