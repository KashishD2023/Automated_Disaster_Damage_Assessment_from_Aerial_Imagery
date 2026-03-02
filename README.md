# 🌋 Project Fuego — Disaster Damage Assessment

AI-powered satellite imagery analysis for wildfire damage assessment. Upload pre and post-disaster satellite images and get per-building damage classifications powered by Google Gemini.

**Course:** Automated Disaster Damage Assessment from Aerial Imagery  
**Data:** xView2 Satellite Imagery (Santa Rosa Wildfire)

---

## 📸 What It Does

- Compares pre/post disaster satellite images side by side
- Classifies every building as `no-damage`, `minor-damage`, or `destroyed`
- Displays results on an interactive map with color-coded building polygons
- Compares AI predictions against ground truth labels for accuracy scoring
- Includes a Gemini-powered chatbot to answer questions about the results

---

## 🚀 Quickstart (Docker)

**Prerequisites:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

**Steps:**

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <repo-folder>

# 2. Create your environment file
cp .env.example .env
```

Open `.env` and add your API key:

```
GOOGLE_API_KEY=your-key-here
MODEL_NAME=gemini-3-pro-preview
```

```bash
# 3. Build and run
docker compose up --build
```

Then open your browser to **http://localhost:8501**

To stop:
```bash
docker compose down
```

---

## 🗂️ Project Structure

```
project/
├── app.py                  # Streamlit web UI (main entry point)
├── ai_damage_detector.py   # Gemini AI classification module
├── organize_files.py       # Step 1: Raw data ingestion & sorting
├── strip_damage_labels.py  # Step 2: Data prep (simulates unlabeled data)
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── data/
    └── santa_rosa_demo/
        ├── pre/            # Pre-disaster satellite PNGs (1024x1024)
        ├── post/           # Post-disaster satellite PNGs (1024x1024)
        ├── fema/           # Stripped label JSONs (polygons only, no damage)
        └── ground_truth/   # Original label JSONs (with damage labels)
```

---

## 🛠️ Setting Up Your Own Data

If you want to use your own xView2 data instead of the included Santa Rosa demo:

**1. Configure the source directory**

Open `organize_files.py` and update `SOURCE_DIR` to point to your downloaded data:

```python
SOURCE_DIR = "/Users/yourname/Downloads/santarosa_photos"
```

**2. Ingest the raw data**

```bash
docker compose run fuego python organize_files.py
```

**3. Strip the damage labels**

```bash
docker compose run fuego python strip_damage_labels.py
```

---

## 🗺️ Usage

1. Select a satellite tile from the dropdown
2. Review the pre/post disaster images side by side
3. Click **"Analyze Damage with AI"**
4. Wait for Gemini to classify all buildings
5. View color-coded results on the interactive map
6. Check accuracy against ground truth (if available)
7. Download predictions as JSON if needed

---

## 🎨 Damage Categories

| Color | Level | Description |
|-------|-------|-------------|
| 🟩 Green | `no-damage` | Building intact, no visible changes |
| 🟨 Yellow | `minor-damage` | Minor changes, structurally sound |
| 🟥 Red | `destroyed` | Collapsed, rubble, ash, or foundation only |
| ⬜ Gray | `un-classified` | API call failed (rate limit or error) |

---

## ⚠️ Known Limitations

- **Polygon alignment:** Building polygons on the map may be slightly offset from actual buildings due to estimated tile bounds
- **Rate limits:** Free/preview Gemini tiers have strict limits — large tiles may take several minutes
- **Basemap mismatch:** The Esri satellite basemap shows current imagery, not the xView2 post-disaster images
- **Accuracy:** Ranges from ~40% (subtle damage) to 95%+ (clearly destroyed buildings)

---

## 🧰 Tech Stack

| Component | Technology |
|-----------|------------|
| AI Model | Google Gemini (multimodal vision) |
| Frontend | Streamlit |
| Mapping | Folium + streamlit-folium |
| Data | xView2 satellite imagery |
| Geo Processing | Shapely (WKT polygon parsing) |
| Containerization | Docker |
