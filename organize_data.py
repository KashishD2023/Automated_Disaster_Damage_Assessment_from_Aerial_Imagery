import os
import shutil
from pathlib import Path

# --- CONFIGURATION ---
# Define the source directory where your raw data currently lives
# Note: This is an absolute path on your local machine
SOURCE_DIR = "/Users/rishikyechuri/Documents/ImportantThings/College/CS Project/disaster_project/data/santarosa_photos"

# Define the destination directory within your project structure
OUTPUT_DIR = "./data/santa_rosa_demo"  # This will be created in your project folder

# Define subdirectories for organized data
PRE_DIR = os.path.join(OUTPUT_DIR, "pre")  # For pre-disaster images
POST_DIR = os.path.join(OUTPUT_DIR, "post")  # For post-disaster images
LABEL_DIR = os.path.join(OUTPUT_DIR, "fema")  # For JSON label files (ground truth)

# Create output directories (script does this automatically)
# exist_ok=True prevents errors if the directories already exist
os.makedirs(PRE_DIR, exist_ok=True)
os.makedirs(POST_DIR, exist_ok=True)
os.makedirs(LABEL_DIR, exist_ok=True)


def organize_files(source_dir):
    """Automatically separate pre/post images and labels"""

    # Validation: Ensure the source directory actually exists before starting
    if not os.path.exists(source_dir):
        print(f"Error: {source_dir} not found!")
        return

    # Initialize counters for the summary report
    pre_count = 0
    post_count = 0
    label_count = 0

    # Get all files (including subdirectories if needed)
    # os.walk allows us to recursively search through folders if the source data is nested
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            source_path = os.path.join(root, filename)

            # Skip hidden files (like .DS_Store on macOS) to avoid clutter/errors
            if filename.startswith('.'):
                continue

            # Separate by type - match any wildfire-related files based on naming convention

            # 1. Pre-disaster images -> ./data/santa_rosa_demo/pre
            if "_pre_disaster.png" in filename:
                shutil.copy2(source_path, os.path.join(PRE_DIR, filename))
                pre_count += 1
                print(f"✓ PRE: {filename}")

            # 2. Post-disaster images -> ./data/santa_rosa_demo/post
            elif "_post_disaster.png" in filename:
                shutil.copy2(source_path, os.path.join(POST_DIR, filename))
                post_count += 1
                print(f"✓ POST: {filename}")

            # 3. Pre-disaster JSON labels -> ./data/santa_rosa_demo/fema
            elif "_pre_disaster.json" in filename:
                shutil.copy2(source_path, os.path.join(LABEL_DIR, filename))
                label_count += 1
                print(f"✓ LABEL (pre): {filename}")

            # 4. Post-disaster JSON labels -> ./data/santa_rosa_demo/fema
            elif "_post_disaster.json" in filename:
                shutil.copy2(source_path, os.path.join(LABEL_DIR, filename))
                label_count += 1
                print(f"✓ LABEL (post): {filename}")

    # --- REPORT ---
    # Print summary statistics to confirm successful organization
    print(f"\n--- SUMMARY ---")
    print(f"Pre-disaster images: {pre_count}")
    print(f"Post-disaster images: {post_count}")
    print(f"Label files: {label_count}")
    print(f"\nFiles organized into: {OUTPUT_DIR}")

    # Warning if nothing was moved (helps debug incorrect paths or empty folders)
    if pre_count == 0 and post_count == 0:
        print("\n⚠️ WARNING: No files found! Make sure your source folder contains files like:")
        print("  - santa-rosa-wildfire_00000001_pre_disaster.png")
        print("  - santa-rosa-wildfire_00000001_post_disaster.png")
        print("  - santa-rosa-wildfire_00000001_post_disaster.json")


if __name__ == "__main__":
    organize_files(SOURCE_DIR)