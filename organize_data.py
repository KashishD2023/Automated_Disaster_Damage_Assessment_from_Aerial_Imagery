import os
import shutil
from pathlib import Path

# --- CONFIGURATION ---
SOURCE_DIR = "/Users/rishikyechuri/Documents/ImportantThings/College/CS Project/disaster_project/data/santarosa_photos"
OUTPUT_DIR = "./data/santa_rosa_demo"  # This will be created in your project folder

PRE_DIR = os.path.join(OUTPUT_DIR, "pre")
POST_DIR = os.path.join(OUTPUT_DIR, "post")
LABEL_DIR = os.path.join(OUTPUT_DIR, "fema")

# Create output directories (script does this automatically)
os.makedirs(PRE_DIR, exist_ok=True)
os.makedirs(POST_DIR, exist_ok=True)
os.makedirs(LABEL_DIR, exist_ok=True)


def organize_files(source_dir):
    """Automatically separate pre/post images and labels"""

    if not os.path.exists(source_dir):
        print(f"Error: {source_dir} not found!")
        return

    pre_count = 0
    post_count = 0
    label_count = 0

    # Get all files (including subdirectories if needed)
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            source_path = os.path.join(root, filename)

            # Skip hidden files
            if filename.startswith('.'):
                continue

            # Separate by type - match any wildfire-related files
            if "_pre_disaster.png" in filename:
                shutil.copy2(source_path, os.path.join(PRE_DIR, filename))
                pre_count += 1
                print(f"✓ PRE: {filename}")

            elif "_post_disaster.png" in filename:
                shutil.copy2(source_path, os.path.join(POST_DIR, filename))
                post_count += 1
                print(f"✓ POST: {filename}")

            elif "_pre_disaster.json" in filename:
                shutil.copy2(source_path, os.path.join(LABEL_DIR, filename))
                label_count += 1
                print(f"✓ LABEL (pre): {filename}")

            elif "_post_disaster.json" in filename:
                shutil.copy2(source_path, os.path.join(LABEL_DIR, filename))
                label_count += 1
                print(f"✓ LABEL (post): {filename}")

    print(f"\n--- SUMMARY ---")
    print(f"Pre-disaster images: {pre_count}")
    print(f"Post-disaster images: {post_count}")
    print(f"Label files: {label_count}")
    print(f"\nFiles organized into: {OUTPUT_DIR}")

    if pre_count == 0 and post_count == 0:
        print("\n⚠️ WARNING: No files found! Make sure your source folder contains files like:")
        print("  - santa-rosa-wildfire_00000001_pre_disaster.png")
        print("  - santa-rosa-wildfire_00000001_post_disaster.png")
        print("  - santa-rosa-wildfire_00000001_post_disaster.json")


if __name__ == "__main__":
    organize_files(SOURCE_DIR)