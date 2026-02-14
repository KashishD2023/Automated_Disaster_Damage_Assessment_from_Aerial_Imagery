"""
app.py
======

Streamlit web application for disaster damage assessment.

This is the main UI entry point. It provides:
    1. Image pair selection (pre/post disaster satellite tiles)
    2. AI-powered damage classification via Gemini (through ai_damage_detector.py)
    3. Interactive folium map with color-coded building polygons
    4. Damage statistics dashboard
    5. Ground truth accuracy comparison (if ground_truth/ dir exists)
    6. Per-building detail view and JSON export

RUN:
    streamlit run app.py

PREREQUISITES:
    - GOOGLE_API_KEY environment variable set
    - Data directory structure:
        data/santa_rosa_demo/
            pre/          → Pre-disaster satellite PNGs
            post/         → Post-disaster satellite PNGs
            fema/         → Stripped label JSONs (polygons only, no damage)
            ground_truth/ → Original label JSONs with damage labels (for accuracy comparison)
    - Run strip_damage_labels.py first to create the stripped/ground_truth split

DEPENDENCIES:
    streamlit, folium, streamlit-folium, shapely, Pillow, google-genai
"""

import streamlit as st
import json
import os
import glob
import folium
from shapely.wkt import loads as wkt_loads
from shapely.geometry import mapping
from streamlit_folium import folium_static
from ai_damage_detector import DamageDetector

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(layout="wide", page_title="Disaster Assessment AI")

# =============================================================================
# DAMAGE LEVEL COLOR MAPPING
# =============================================================================
# These colors are used for both the folium map polygons and the UI legend.
# Only 3 damage levels + un-classified (for failed API calls).
# Matches the xView2/FEMA ground truth label vocabulary.
DAMAGE_COLOR = {
    "no-damage": "#00ff00",      # Green
    "minor-damage": "#ffff00",   # Yellow
    "destroyed": "#ff0000",      # Red
    "un-classified": "#808080",  # Gray (API failure or missing result)
}

# Fill opacity for the colored polygon overlays on the map
DAMAGE_FILL_OPACITY = {
    "no-damage": 0.5,
    "minor-damage": 0.5,
    "destroyed": 0.6,
    "un-classified": 0.3,
}

# =============================================================================
# HEADER
# =============================================================================
st.title("🌋 Project Fuego: Disaster Damage Assessment")
st.markdown("**Powered by** Gemini 3 Pro | **Data:** xView2 Satellite Imagery")

# =============================================================================
# SECTION 1: IMAGE PAIR SELECTION
# =============================================================================
# Scans the data directory for matching pre/post/label file triplets.
# Files are matched by their base name (e.g., "santa-rosa-wildfire_00000012"):
#   - pre/santa-rosa-wildfire_00000012_pre_disaster.png
#   - post/santa-rosa-wildfire_00000012_post_disaster.png
#   - fema/santa-rosa-wildfire_00000012_post_disaster.json
st.subheader("📂 Select Image Pair")

PRE_DIR = "./data/santa_rosa_demo/pre"
POST_DIR = "./data/santa_rosa_demo/post"
FEMA_DIR = "./data/santa_rosa_demo/fema"           # Stripped JSONs (no damage labels)
GROUND_TRUTH_DIR = "./data/santa_rosa_demo/ground_truth"  # Original JSONs (with damage labels)

# Find all post-disaster images and match them with pre images + label files
post_images = sorted(glob.glob(os.path.join(POST_DIR, "*_post_disaster.png")))
available_pairs = []

for post_path in post_images:
    filename = os.path.basename(post_path)
    # Extract base name: "santa-rosa-wildfire_00000012" from "..._post_disaster.png"
    base_name = filename.replace("_post_disaster.png", "")
    pre_path = os.path.join(PRE_DIR, f"{base_name}_pre_disaster.png")
    label_path = os.path.join(FEMA_DIR, f"{base_name}_post_disaster.json")
    # Only include pairs where all three files exist
    if os.path.exists(pre_path) and os.path.exists(label_path):
        available_pairs.append({
            "name": base_name,
            "pre": pre_path,
            "post": post_path,
            "label": label_path,
        })

# Halt if no valid data found
if not available_pairs:
    st.error("⚠️ No valid image pairs with labels found. Ensure data/santa_rosa_demo/ has pre/, post/, and fema/ folders.")
    st.stop()

# Dropdown to select which tile to analyze
selected_name = st.selectbox(
    f"Choose an image pair ({len(available_pairs)} available):",
    [p["name"] for p in available_pairs],
)
selected_pair = next(p for p in available_pairs if p["name"] == selected_name)

# Display pre and post images side by side for visual comparison
col_pre, col_post = st.columns(2)
with col_pre:
    st.image(selected_pair["pre"], caption="PRE-disaster", use_column_width=True)
with col_post:
    st.image(selected_pair["post"], caption="POST-disaster", use_column_width=True)

# Show how many buildings the label file contains (before running AI)
with open(selected_pair["label"], 'r') as f:
    label_data = json.load(f)
building_count = len(label_data.get('features', {}).get('lng_lat', []))
st.info(f"📍 {building_count} building polygons found in label file")

# =============================================================================
# SECTION 2: AI ANALYSIS TRIGGER
# =============================================================================
# Uses st.form to prevent accidental re-runs — analysis ONLY starts when the
# user explicitly clicks the submit button.
# Results are cached in st.session_state so they persist across Streamlit reruns.
st.divider()

if "results_cache" not in st.session_state:
    st.session_state.results_cache = {}

with st.form("analysis_form"):
    # Batch size controls how many buildings are sent per Gemini API call.
    # Higher = fewer API calls (good for rate limits) but longer prompts.
    # 85 is recommended for Gemini Pro.
    batch_size = st.selectbox("Batch size (buildings per API call):", [25, 50, 85, 170], index=2,
                              help="Larger = fewer API calls. 85 recommended for Pro.")
    analyze_btn = st.form_submit_button("🔍 Analyze Damage with AI", type="primary")

if analyze_btn:
    # Show progress indicators while AI is working
    progress_text = st.empty()
    progress_bar = st.progress(0)

    try:
        detector = DamageDetector()
        progress_text.text("Initializing AI...")

        # Run the full analysis pipeline (see ai_damage_detector.py for details)
        results = detector.analyze_tile(
            selected_pair["pre"],
            selected_pair["post"],
            selected_pair["label"],
            batch_size=batch_size,
        )
        # Cache results so they survive Streamlit reruns
        st.session_state.results_cache[selected_name] = results
        progress_bar.progress(1.0)
        progress_text.text("")
        st.success(f"✅ Classified {len(results)} buildings!")
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# =============================================================================
# SECTION 3: MAP DISPLAY
# =============================================================================
# If we have results (either just computed or from cache), display them on
# an interactive folium map with color-coded building polygons.
results = st.session_state.results_cache.get(selected_name)

if results:
    st.divider()
    st.subheader("🗺️ Damage Assessment Map")

    # Build a UID → damage lookup from the AI results
    # This lets us quickly match each polygon to its classification
    uid_to_damage = {}
    for r in results:
        uid_to_damage[r.get('uid', '')] = {
            'damage': r.get('damage', 'un-classified'),
            'confidence': r.get('confidence', 0),
            'description': r.get('description', ''),
        }

    # Parse polygon geometries from the label file and pair with AI results
    polygons = label_data.get('features', {}).get('lng_lat', [])
    all_lats = []  # Collected for computing map center and bounds
    all_lngs = []
    features_for_map = []

    for poly_data in polygons:
        wkt_str = poly_data.get('wkt', '')
        uid = poly_data.get('properties', {}).get('uid', '')

        try:
            # Parse the WKT polygon string into a shapely geometry
            geom = wkt_loads(wkt_str)
            coords = list(geom.exterior.coords)
            lngs = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            all_lngs.extend(lngs)
            all_lats.extend(lats)

            # Look up the AI's damage classification for this building
            ai_result = uid_to_damage.get(uid, {
                'damage': 'un-classified',
                'confidence': 0,
                'description': 'Not classified',
            })

            features_for_map.append({
                'geom': geom,
                'uid': uid,
                'damage': ai_result['damage'],
                'confidence': ai_result['confidence'],
                'description': ai_result['description'],
            })
        except Exception:
            continue

    if not features_for_map:
        st.warning("No valid polygons to display")
        st.stop()

    # --- Create the folium map ---
    # Center on the average of all polygon coordinates
    center_lat = sum(all_lats) / len(all_lats)
    center_lng = sum(all_lngs) / len(all_lngs)

    # Use Esri World Imagery as the base layer (satellite view)
    # NOTE: This shows the area in its current/pre-disaster state since it's
    # a generic satellite basemap, not the xView2 post-disaster imagery.
    # The building polygons will be slightly offset from the Esri imagery
    # because the geo-to-pixel mapping in the detector uses estimated tile bounds.
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=17,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
    )

    # --- Draw each building polygon on the map ---
    for feat in features_for_map:
        damage = feat['damage']
        color = DAMAGE_COLOR.get(damage, "#808080")
        fill_opacity = DAMAGE_FILL_OPACITY.get(damage, 0.3)

        # Folium expects coordinates as (lat, lng), but shapely stores them as (lng, lat)
        poly_coords = [(lat, lng) for lng, lat in feat['geom'].exterior.coords]

        # Format confidence for tooltip display
        conf = feat.get('confidence', 0)
        if isinstance(conf, (int, float)):
            conf_str = f"{conf:.0%}" if conf <= 1 else f"{conf}%"
        else:
            conf_str = str(conf)
        tooltip_text = f"{damage} ({conf_str}) - {feat['uid'][:8]}"

        # Add the colored polygon to the map
        folium.Polygon(
            locations=poly_coords,
            color=color,          # Border color
            fill=True,
            fill_color=color,     # Fill color
            fill_opacity=fill_opacity,
            weight=2,             # Border thickness
            tooltip=tooltip_text, # Shown on hover
        ).add_to(m)

    # Zoom the map to fit all polygons
    m.fit_bounds([[min(all_lats), min(all_lngs)], [max(all_lats), max(all_lngs)]])

    # Render the map (folium_static avoids JSON serialization issues with st_folium)
    folium_static(m, width=1200, height=600)

    # ==========================================================================
    # SECTION 4: LEGEND
    # ==========================================================================
    st.markdown("""
    | Color | Damage Level |
    |-------|-------------|
    | 🟩 | No Damage |
    | 🟨 | Minor Damage |
    | 🟥 | Destroyed |
    """)

    # ==========================================================================
    # SECTION 5: DAMAGE STATISTICS
    # ==========================================================================
    # Simple counts and percentages of each damage category
    st.divider()
    st.subheader("📊 Damage Statistics")

    total = len(results)
    destroyed = sum(1 for r in results if r.get("damage") == "destroyed")
    minor = sum(1 for r in results if r.get("damage") == "minor-damage")
    no_damage = sum(1 for r in results if r.get("damage") == "no-damage")
    unclassified = sum(1 for r in results if r.get("damage") == "un-classified")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Buildings", total)
    m2.metric("No Damage", no_damage, delta=f"{no_damage/total*100:.0f}%" if total else "0%", delta_color="normal")
    m3.metric("Minor Damage", minor, delta=f"{minor/total*100:.0f}%" if total else "0%", delta_color="off")
    m4.metric("Destroyed", destroyed, delta=f"{destroyed/total*100:.0f}%" if total else "0%", delta_color="inverse")

    # ==========================================================================
    # SECTION 6: GROUND TRUTH ACCURACY COMPARISON
    # ==========================================================================
    # If the ground_truth/ directory has the original (unstripped) label file
    # for this tile, compare AI predictions against the real damage labels.
    # This section only appears if the ground truth file exists.
    gt_path = os.path.join(GROUND_TRUTH_DIR, f"{selected_name}_post_disaster.json")
    if os.path.exists(gt_path):
        st.divider()
        st.subheader("🎯 Accuracy vs Ground Truth")

        with open(gt_path, 'r') as f:
            gt_data = json.load(f)

        # Build a UID → ground truth damage label lookup
        gt_polygons = gt_data.get('features', {}).get('lng_lat', [])
        gt_lookup = {}
        for p in gt_polygons:
            uid = p.get('properties', {}).get('uid', '')
            subtype = p.get('properties', {}).get('subtype', 'unknown')
            gt_lookup[uid] = subtype

        # Compare each AI prediction against the ground truth
        correct = 0
        total_compared = 0
        confusion = {}  # (ground_truth_label, ai_label) → count

        for r in results:
            uid = r.get('uid', '')
            ai_damage = r.get('damage', 'un-classified')
            gt_damage = gt_lookup.get(uid)

            # Skip buildings with no ground truth or un-classified ground truth
            if gt_damage and gt_damage != 'un-classified':
                total_compared += 1
                if ai_damage == gt_damage:
                    correct += 1
                # Track confusion matrix entries
                key = (gt_damage, ai_damage)
                confusion[key] = confusion.get(key, 0) + 1

        if total_compared > 0:
            accuracy = correct / total_compared * 100
            st.metric("Overall Accuracy", f"{accuracy:.1f}%", delta=f"{correct}/{total_compared} correct")

            # Show detailed confusion matrix in an expandable section
            with st.expander("Confusion Details"):
                for (gt, ai), count in sorted(confusion.items(), key=lambda x: -x[1]):
                    match = "✅" if gt == ai else "❌"
                    st.write(f"{match} Ground Truth: **{gt}** → AI: **{ai}** ({count}x)")
        else:
            st.info("No comparable ground truth labels found for this tile.")

    # ==========================================================================
    # SECTION 7: PER-BUILDING DETAILS
    # ==========================================================================
    # Expandable list showing each building's UID, damage level, confidence,
    # and the AI's text description of observed damage.
    st.divider()
    st.subheader("🏠 Building Details")
    for r in results:
        damage = r.get("damage", "unknown")
        # Map damage level to colored emoji for visual scanning
        color_hex = {
            "no-damage": "🟩", "minor-damage": "🟨",
            "destroyed": "🟥"
        }.get(damage, "⬜")

        with st.expander(f"{color_hex} {r.get('uid', '?')[:12]}... — {damage} ({r.get('confidence', 0):.0%})"):
            st.write(r.get("description", "No description available."))

    # ==========================================================================
    # SECTION 8: JSON EXPORT
    # ==========================================================================
    # Download button for the raw AI predictions as a JSON file.
    # Useful for further analysis, integration with other tools, or archiving.
    st.divider()
    st.download_button(
        "💾 Download AI Predictions (JSON)",
        data=json.dumps(results, indent=2),
        file_name=f"{selected_name}_ai_predictions.json",
        mime="application/json",
    )

# =============================================================================
# NO RESULTS STATE
# =============================================================================
# Shown when no analysis has been run yet or the AI returned empty results.
elif selected_name not in st.session_state.results_cache:
    st.info("👆 Select an image pair and click **Analyze Damage with AI** to get started.")
else:
    st.warning("AI returned no results for this image pair.")