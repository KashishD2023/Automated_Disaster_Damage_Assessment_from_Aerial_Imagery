Automated_Disaster_Damage_Assessment_from_Aerial_Imagery
Proffesor Dinc


Project Structure

project/
├── app.py                    # Streamlit web UI (main entry point)
├── ai_damage_detector.py     # Gemini AI classification module
├── organize_files.py         # Step 1: Raw data ingestion & sorting script
├── strip_damage_labels.py    # Step 2: Data prep script (simulates unlabeled data)
└── data/
    └── santa_rosa_demo/
        ├── pre/              # Pre-disaster satellite PNGs (1024x1024)
        ├── post/             # Post-disaster satellite PNGs (1024x1024)
        ├── fema/             # Stripped label JSONs (polygons only, no damage)
        └── ground_truth/     # Original label JSONs (with damage labels)

Filesapp.py — Streamlit Web ApplicationThe main UI. Provides the full workflow in one page:Image pair selector: Dropdown to pick a satellite tile. Shows pre/post images side by side.AI analysis: Click a button to run Gemini classification on all buildings in the selected tile. Uses st.form to prevent accidental re-triggers.Interactive map: Folium map with Esri satellite basemap. 
Each building polygon is color-coded by its AI-assigned damage level. Hover for details.Statistics dashboard: Building counts and percentages per damage category.Ground truth comparison: If ground_truth/ data exists, shows overall accuracy percentage and a confusion matrix breakdown.Building details: Expandable list of every building with UID, damage level, confidence, and AI description.JSON export: Download button for raw AI predictions.Key technical notes:Uses folium_static (not st_folium) to avoid JSON serialization errors.Results are cached in st.session_state so they persist across Streamlit reruns.ai_damage_detector.py — AI Classification ModuleCore module that handles all Gemini API interaction. Contains the DamageDetector class.Architecture: Does NOT detect buildings. 
Building polygons come from the stripped FEMA JSONs. The AI only classifies damage by comparing pre/post imagery.Pipeline (analyze_tile method):Loads the stripped label JSON (building polygons with UIDs, no damage labels).Parses WKT polygon geometries and extracts lng/lat coordinates.Estimates tile geographic bounds from polygon extent (adds 10% margin).Converts each polygon's lng/lat coordinates to pixel bounding boxes.Sends full pre+post images to Gemini in batches, with a text list of building pixel locations.Gemini classifies each building and returns JSON with damage levels.Key technical notes:Batching: Buildings are grouped into batches (default 85) to minimize API calls while staying under rate limits.Rate limit handling: Automatically detects 429 errors, waits, and retries (up to 5 attempts).
Prompt Engineering: Restricts damage labels to exactly 3 categories (no-damage, minor-damage, destroyed) to match xView2 ground truth vocabulary.organize_files.py — Raw Data Ingestion ScriptRun this first. This script automates the setup of the project directory by ingesting raw xView2 dataset files.Input: Scans a raw source folder (defined in the SOURCE_DIR variable).
Logic: Recursively walks through the source, filters files by suffix, and sorts them.Output: Creates the data/santa_rosa_demo/ directory and populates the pre/, post/, and fema/ subfolders automatically.Note: You must edit the SOURCE_DIR variable inside this script to point to your local download of the xView2 dataset before running.strip_damage_labels.py — Data Preparation ScriptRun this second. It splits the organized FEMA label JSONs into two versions:Stripped (overwrites fema/): Same building polygons but with subtype (damage level) and feature_type fields removed. This is what the AI receives.Ground truth (saved to ground_truth/): Exact copies of the original files with damage labels intact. Used by the app for accuracy comparison.What gets stripped:properties.subtype (e.g., "destroyed", "no-damage") — removedproperties.feature_type (e.g., "building") — removedproperties.uid — preserved (needed to match AI results back to polygons)wkt polygon geometry — preserved (the building footprint)SetupPrerequisitesPython 3.9+Google Gemini API key (get one here)xView2 satellite imagery data (Santa Rosa wildfire subset)InstallationBash# Clone the repo
git clone <repo-url>
cd Automated_Disaster_Damage_Assessment_from_Aerial_Imagery

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install streamlit folium streamlit-folium shapely Pillow google-genai

# Set your API key
export GOOGLE_API_KEY="your-key-here"
Data PreparationConfigure Source Data:Open organize_files.py and update the SOURCE_DIR variable to point to where you downloaded the raw photos.PythonSOURCE_DIR = "/Users/yourname/Downloads/santarosa_photos"
Ingest Data:Bashpython organize_files.py
Output: Creates data/santa_rosa_demo and sorts images/labels into folders.Strip Labels:Bashpython strip_damage_labels.py
Output: Creates the ground_truth/ backup and strips damage tags from fema/.Run the AppBashstreamlit run app.py
Then open http://localhost:8501 in your browser.UsageSelect a satellite tile from the dropdown.Review the pre/post disaster images.Click "Analyze Damage with AI".Wait for Gemini to classify all buildings (progress shown in terminal).View results on the interactive map.Check accuracy against ground truth (if available).Download predictions as JSON if needed.Data FormatLabel JSON Structure (xView2 format)Stripped (fema/) — what the AI receives:JSON{
  "features": {
    "lng_lat": [
      {
        "properties": {
          "uid": "f41834a1-4012-4f7a-b2e9-7b194dfa66d0"
        },
        "wkt": "POLYGON ((-122.746 38.501, -122.747 38.502, ...))"
      }
    ]
  }
}
Ground truth (ground_truth/) — used for accuracy comparison:JSON{
  "features": {
    "lng_lat": [
      {
        "properties": {
          "feature_type": "building",
          "subtype": "destroyed",
          "uid": "f41834a1-4012-4f7a-b2e9-7b194dfa66d0"
        },
        "wkt": "POLYGON ((-122.746 38.501, -122.747 38.502, ...))"
      }
    ]
  }
}
AI Output FormatJSON[
  {
    "uid": "f41834a1-4012-4f7a-b2e9-7b194dfa66d0",
    "damage": "destroyed",
    "confidence": 0.95,
    "description": "Building reduced to rubble, only foundation visible"
  }
]
Damage CategoriesLevelColorDescriptionno-damage🟩 GreenBuilding intact, no visible changesminor-damage🟨 YellowMinor cosmetic changes, structurally sounddestroyed🟥 RedCollapsed, rubble, ash, or foundation onlyun-classified⬜ GrayAPI call failed (rate limit, error, etc.)Known LimitationsPolygon alignment: The geo-to-pixel coordinate conversion uses estimated tile bounds (10% margin around polygon extent). This means building polygons on the Esri basemap may be slightly offset from the actual buildings.Rate limits: Google's free/preview API tiers have strict rate limits. The app handles this with automatic retry, but large tiles may take several minutes.Basemap mismatch: The Esri satellite basemap shows current/pre-disaster imagery, while the analysis uses xView2 post-disaster images.Classification accuracy: Varies by tile. Tiles with clearly destroyed buildings achieve 95%+ accuracy. Tiles with subtle damage can drop to ~40% as the AI may hallucinate damage from lighting/seasonal differences.Tech StackAI Model: Google Gemini 3 Pro Preview (multimodal vision)Frontend: StreamlitMapping: Folium + streamlit-foliumData: xView2 satellite imagery dataset (Santa Rosa wildfire)Geo Processing: Shapely (WKT polygon parsing)