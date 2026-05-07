import streamlit as st
import json
import os
import glob
import time
import folium
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image

from google import genai
from google.genai import types
from shapely.wkt import loads as wkt_loads
from streamlit_folium import st_folium
from folium.raster_layers import ImageOverlay
from ai_damage_detector import DamageDetector

# =============================================================================
# LOAD PERSON 6 CHATBOT QUESTION TYPES
# =============================================================================
QUESTIONS_PATH = Path("docs/docs/chatbot_questions.md")
try:
    CHATBOT_QUESTION_TYPES = (
        QUESTIONS_PATH.read_text(encoding="utf-8")
        if QUESTIONS_PATH.exists()
        else ""
    )
except Exception:
    CHATBOT_QUESTION_TYPES = ""

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(layout="wide", page_title="Disaster Assessment AI")

# =============================================================================
# GLOBAL STYLES
# =============================================================================
st.markdown(
    """
    <style>
    .thinking-bubbles {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 0;
        min-height: 24px;
    }

    .thinking-bubbles span {
        width: 8px;
        height: 8px;
        background-color: #9aa0a6;
        border-radius: 50%;
        display: inline-block;
        animation: thinking-bounce 1.4s infinite ease-in-out both;
    }

    .thinking-bubbles span:nth-child(1) {
        animation-delay: -0.32s;
    }

    .thinking-bubbles span:nth-child(2) {
        animation-delay: -0.16s;
    }

    .thinking-bubbles span:nth-child(3) {
        animation-delay: 0s;
    }

    @keyframes thinking-bounce {
        0%, 80%, 100% {
            transform: scale(0.6);
            opacity: 0.4;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# MODEL CONFIG
# =============================================================================
DEFAULT_CHAT_MODEL = os.getenv("MODEL_NAME", "gemini-2.5-flash")
FAST_CHAT_MODEL = "gemini-2.5-flash"

# =============================================================================
# DAMAGE LEVEL COLOR MAPPING
# =============================================================================
DAMAGE_COLOR = {
    "no-damage": "#00ff00",
    "minor-damage": "#ffff00",
    "destroyed": "#ff0000",
    "un-classified": "#808080",
}

DAMAGE_FILL_OPACITY = {
    "no-damage": 0.5,
    "minor-damage": 0.5,
    "destroyed": 0.6,
    "un-classified": 0.3,
}

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
PRE_DIR = "./data/santa_rosa_demo/pre"
POST_DIR = "./data/santa_rosa_demo/post"
FEMA_DIR = "./data/santa_rosa_demo/fema"
GROUND_TRUTH_DIR = "./data/santa_rosa_demo/ground_truth"

CACHE_FILE = "./data/santa_rosa_demo/results_cache.json"

# =============================================================================
# HELPERS
# =============================================================================
def load_available_pairs():
    post_images = sorted(glob.glob(os.path.join(POST_DIR, "*_post_disaster.png")))
    pairs = []

    for post_path in post_images:
        filename = os.path.basename(post_path)
        base_name = filename.replace("_post_disaster.png", "")
        pre_path = os.path.join(PRE_DIR, f"{base_name}_pre_disaster.png")
        label_path = os.path.join(FEMA_DIR, f"{base_name}_post_disaster.json")

        if os.path.exists(pre_path) and os.path.exists(label_path):
            pairs.append(
                {
                    "name": base_name,
                    "pre": pre_path,
                    "post": post_path,
                    "label": label_path,
                }
            )

    return pairs


def get_bounds_from_label(label_path):
    try:
        with open(label_path, "r") as f:
            data = json.load(f)

        polygons = data.get("features", {}).get("lng_lat", [])
        all_lats = []
        all_lngs = []

        for poly_data in polygons:
            wkt_str = poly_data.get("wkt", "")
            if not wkt_str:
                continue

            try:
                geom = wkt_loads(wkt_str)
                coords = list(geom.exterior.coords)
                for lng, lat in coords:
                    all_lngs.append(lng)
                    all_lats.append(lat)
            except Exception:
                continue

        if not all_lats or not all_lngs:
            return None

        return [[min(all_lats), min(all_lngs)], [max(all_lats), max(all_lngs)]]
    except Exception:
        return None


def build_combined_tile_data(pairs):
    all_tiles = []

    for pair in pairs:
        bounds = get_bounds_from_label(pair["label"])
        if not bounds:
            continue

        all_tiles.append(
            {
                "name": pair["name"],
                "pre": pair["pre"],
                "post": pair["post"],
                "label": pair["label"],
                "bounds": bounds,
            }
        )

    return all_tiles


@st.cache_data
def image_to_data_url(image_path):
    with Image.open(image_path) as img:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{encoded}"

@st.cache_data
def build_all_features(cache_key, pair_names_key):
    """Build polygon features from every cached tile. Args are hashable cache keys."""
    features = []
    lats = []
    lngs = []

    cache = st.session_state.results_cache
    for tile_name, tile_results in cache.items():
        tile_pair = next((p for p in available_pairs if p["name"] == tile_name), None)
        if not tile_pair:
            continue
        try:
            with open(tile_pair["label"], "r") as f:
                tile_label_data = json.load(f)
        except Exception:
            continue

        uid_to_damage = {
            r.get("uid", ""): {
                "damage": r.get("damage", "un-classified"),
                "confidence": r.get("confidence", 0),
                "description": r.get("description", ""),
            }
            for r in tile_results
        }

        for poly_data in tile_label_data.get("features", {}).get("lng_lat", []):
            wkt_str = poly_data.get("wkt", "")
            uid = poly_data.get("properties", {}).get("uid", "")
            try:
                geom = wkt_loads(wkt_str)
                coords = list(geom.exterior.coords)
                lngs.extend(c[0] for c in coords)
                lats.extend(c[1] for c in coords)
                ai = uid_to_damage.get(uid, {"damage": "un-classified", "confidence": 0, "description": "Not classified"})
                features.append({"tile": tile_name, "geom": geom, "uid": uid, **ai})
            except Exception:
                continue

    return features, lats, lngs

def make_single_interactive_map(all_tiles, selected_name, layer_mode):
    selected_tile = next((t for t in all_tiles if t["name"] == selected_name), None)
    if not selected_tile:
        return None

    south, west = selected_tile["bounds"][0]
    north, east = selected_tile["bounds"][1]
    center_lat = (south + north) / 2
    center_lng = (west + east) / 2

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=17,
        tiles=None,
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Esri Satellite",
        overlay=False,
        control=False,
    ).add_to(m)

    overlay_path = selected_tile["post"] if layer_mode == "Post Disaster" else selected_tile["pre"]

    try:
        image_url = image_to_data_url(overlay_path)
        ImageOverlay(
            image=image_url,
            bounds=selected_tile["bounds"],
            opacity=0.85,
            interactive=False,
            cross_origin=False,
            zindex=1,
        ).add_to(m)
    except Exception as e:
        st.warning(f"Could not render {layer_mode.lower()} overlay: {e}")

    m.fit_bounds(selected_tile["bounds"])
    return m




def analyze_uploaded_images_backend(pre_path, post_path):
    """Analyze user-uploaded pre/post images using Gemini.

    DamageDetector.analyze_tile needs a FEMA/xView2 label JSON file with building
    polygons. User uploads usually do not include that label file, so this backend path
    performs image-level damage assessment instead of per-building polygon classification.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set in your environment.")

    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    pre_bytes = Path(pre_path).read_bytes()
    post_bytes = Path(post_path).read_bytes()

    prompt = """
You are a disaster damage assessment AI.
Compare the PRE disaster image and POST disaster image.
Return a concise damage assessment with these sections:

1. Overall Damage Level: choose one of no-damage, minor-damage, major-damage, destroyed, or uncertain.
2. Visible Changes: describe important visual differences between pre and post imagery.
3. Likely Damaged Areas: identify where damage appears in the image, such as top-left, center, bottom-right.
4. Confidence: give a percentage from 0 to 100.
5. Notes: mention limitations if the images are not aligned, blurry, or not satellite/aerial imagery.

Do not invent exact building counts unless they are clearly visible.
"""

    response = client.models.generate_content(
        model=model_name,
        contents=[
            prompt,
            types.Part.from_bytes(data=pre_bytes, mime_type="image/png"),
            types.Part.from_bytes(data=post_bytes, mime_type="image/png"),
        ],
    )

    return response.text if getattr(response, "text", None) else "No response returned."

# =============================================================================
# HEADER
# =============================================================================
st.title("🔥 Santa Rosa Wildfire: Disaster Damage Assessment")
st.markdown("**Powered by** Gemini | **Data:** xView2 Satellite Imagery")

# =============================================================================
# SESSION STATE SETUP
# =============================================================================
def load_cache_from_disk():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache_to_disk(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

if "results_cache" not in st.session_state:
    st.session_state.results_cache = load_cache_from_disk()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# =============================================================================
# LOAD TILES
# =============================================================================
available_pairs = load_available_pairs()

if not available_pairs:
    st.error(
        "⚠️ No valid image pairs with labels found. Ensure data/santa_rosa_demo/ has pre/, post/, and fema/ folders."
    )
    st.stop()

all_tiles = build_combined_tile_data(available_pairs)

if not all_tiles:
    st.error("⚠️ Could not build geographic bounds for the tiles.")
    st.stop()

# =============================================================================
# TABS
# =============================================================================
tab_map, tab_results, tab_upload = st.tabs(["🗺️ Map", "📊 Results", "📤 Upload Images"])

# =============================================================================
# TAB 1: MAP
# =============================================================================
with tab_map:
    st.subheader("📂 Select a Tile")

    tile_names = [p["name"] for p in available_pairs]

    selected_name = st.selectbox(
        f"Choose a tile ({len(tile_names)} available):",
        tile_names,
        index=0,
    )

    cached_count = len(st.session_state.results_cache)
    if cached_count > 0:
        st.success(f"💾 {cached_count}/{len(tile_names)} tiles already classified and loaded from disk")

    selected_pair = next(p for p in available_pairs if p["name"] == selected_name)

    with open(selected_pair["label"], "r") as f:
        label_data = json.load(f)

    building_count = len(label_data.get("features", {}).get("lng_lat", []))
    st.info(f"📍 {building_count} building polygons found in selected tile")

    results = st.session_state.results_cache.get(selected_name)

    # --- Raw pre/post map (shown before analysis) ---
    if not results:
        layer_mode = st.radio(
            "Map Layer",
            ["Pre Disaster", "Post Disaster"],
            horizontal=True,
            key="main_map_layer_mode",
        )

        st.subheader("🗺 Interactive Tile Map")
        main_map = make_single_interactive_map(all_tiles, selected_name, layer_mode)
        st_folium(
            main_map,
            width=1400,
            height=700,
            returned_objects=[],
            key=f"main_map_{selected_name}_{layer_mode}",
        )

    # --- Analysis controls ---
    st.divider()
    with st.form("analysis_form"):
        batch_size = st.selectbox(
            "Batch size (buildings per API call):",
            [25, 50, 85, 170],
            index=2,
            help="Larger = fewer API calls. 85 recommended for Pro.",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            analyze_btn = st.form_submit_button("🔍 Analyze This Tile", type="primary")
        with col_b:
            analyze_all_btn = st.form_submit_button("🚀 Analyze ALL Tiles", type="secondary")

    if analyze_btn or analyze_all_btn:
        tiles_to_run = available_pairs if analyze_all_btn else [selected_pair]
        overall_progress = st.progress(0)
        status_text = st.empty()

        for tile_idx, pair in enumerate(tiles_to_run):
            status_text.text(f"Analyzing {pair['name']} ({tile_idx + 1}/{len(tiles_to_run)})...")
            progress_text = st.empty()
            progress_bar = st.progress(0)

            max_tile_retries = 3
            for tile_attempt in range(max_tile_retries):
                try:
                    detector = DamageDetector()
                    results = detector.analyze_tile(
                        pair["pre"],
                        pair["post"],
                        pair["label"],
                        batch_size=batch_size,
                    )
                    st.session_state.results_cache[pair["name"]] = results
                    save_cache_to_disk(st.session_state.results_cache)
                    progress_bar.progress(1.0)
                    progress_text.text(f"✅ {pair['name']}: {len(results)} buildings classified")
                    break

                except Exception as e:
                    if tile_attempt < max_tile_retries - 1:
                        wait = 60 * (tile_attempt + 1)
                        status_text.text(
                            f"⚠️ {pair['name']} failed, retrying in {wait}s (attempt {tile_attempt + 1}/{max_tile_retries})..."
                        )
                        time.sleep(wait)
                    else:
                        st.warning(f"⚠️ Skipping {pair['name']} after {max_tile_retries} attempts: {e}")

            overall_progress.progress((tile_idx + 1) / len(tiles_to_run))

        status_text.text("✅ All done!")

    results = st.session_state.results_cache.get(selected_name)

    # --- Cumulative damage map ---
    if st.session_state.results_cache:
        st.divider()
        st.subheader("🗺️ Damage Assessment Map (All Analyzed Tiles)")

        cache_key = tuple(sorted(st.session_state.results_cache.keys()))
        pair_names_key = tuple(p["name"] for p in available_pairs)
        features_for_map, poly_lats, poly_lngs = build_all_features(cache_key, pair_names_key)

        if not features_for_map:
            st.warning("No valid polygons to display")
        else:
            center_lat = sum(poly_lats) / len(poly_lats)
            center_lng = sum(poly_lngs) / len(poly_lngs)

            damage_bg_mode = st.radio(
                "Selected-tile background",
                ["Pre Disaster", "Post Disaster"],
                horizontal=True,
                key="damage_map_bg_mode",
            )

            m = folium.Map(
                location=[center_lat, center_lng],
                zoom_start=18,
                tiles=None,
            )

            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri World Imagery",
                name="Esri Satellite",
                overlay=False,
                control=False,
            ).add_to(m)

            # Overlay only the selected tile's PNG (keeps map light)
            selected_bounds = get_bounds_from_label(selected_pair["label"])
            bg_image_path = (
                selected_pair["pre"] if damage_bg_mode == "Pre Disaster" else selected_pair["post"]
            )
            if selected_bounds:
                try:
                    image_url = image_to_data_url(bg_image_path)
                    ImageOverlay(
                        image=image_url,
                        bounds=selected_bounds,
                        opacity=0.72,
                        interactive=False,
                        cross_origin=False,
                        zindex=1,
                    ).add_to(m)
                except Exception as e:
                    st.warning(f"Could not render damage map background: {e}")

            # Draw polygons for every analyzed tile
            for feat in features_for_map:
                damage = feat["damage"]
                color = DAMAGE_COLOR.get(damage, "#808080")
                fill_opacity = DAMAGE_FILL_OPACITY.get(damage, 0.3)
                poly_coords = [(lat, lng) for lng, lat in feat["geom"].exterior.coords]

                conf = feat.get("confidence", 0)
                if isinstance(conf, (int, float)):
                    conf_str = f"{conf:.0%}" if conf <= 1 else f"{conf}%"
                else:
                    conf_str = str(conf)

                tooltip_text = f"[{feat.get('tile', '?')}] {damage} ({conf_str}) - {feat['uid'][:8]}"

                folium.Polygon(
                    locations=poly_coords,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=fill_opacity,
                    weight=2,
                    tooltip=tooltip_text,
                ).add_to(m)

            # Center on selected tile, let user zoom out for the rest
            if selected_bounds:
                m.fit_bounds(selected_bounds)
            else:
                m.fit_bounds([[min(poly_lats), min(poly_lngs)], [max(poly_lats), max(poly_lngs)]])

            st_folium(
                m,
                width=1400,
                height=650,
                returned_objects=[],
                key=f"damage_map_{selected_name}_{damage_bg_mode}_{len(cache_key)}",
            )

            st.markdown(
                """
                | Color | Damage Level |
                |-------|-------------|
                | 🟩 | No Damage |
                | 🟨 | Minor Damage |
                | 🟥 | Destroyed |
                | ⬜ | Un-classified |
                """
            )

# =============================================================================
# TAB 2: RESULTS
# =============================================================================
with tab_results:
    if not st.session_state.results_cache:
        st.info("👆 Go to the Map tab and analyze a tile to see results here.")
    else:
        # --- Cumulative stats across every analyzed tile ---
        all_results_flat = []
        for tile_results in st.session_state.results_cache.values():
            all_results_flat.extend(tile_results)

        st.subheader(f"📊 Cumulative Stats — {len(st.session_state.results_cache)} tile(s) analyzed")

        total = len(all_results_flat)
        destroyed = sum(1 for r in all_results_flat if r.get("damage") == "destroyed")
        minor = sum(1 for r in all_results_flat if r.get("damage") == "minor-damage")
        no_damage = sum(1 for r in all_results_flat if r.get("damage") == "no-damage")
        unclassified = sum(1 for r in all_results_flat if r.get("damage") == "un-classified")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Buildings", total)
        c2.metric(
            "No Damage",
            no_damage,
            delta=f"{no_damage/total*100:.0f}%" if total else "0%",
            delta_color="normal",
        )
        c3.metric(
            "Minor Damage",
            minor,
            delta=f"{minor/total*100:.0f}%" if total else "0%",
            delta_color="off",
        )
        c4.metric(
            "Destroyed",
            destroyed,
            delta=f"{destroyed/total*100:.0f}%" if total else "0%",
            delta_color="inverse",
        )

        if unclassified > 0:
            st.metric(
                "Un-classified",
                unclassified,
                delta=f"{unclassified/total*100:.0f}%" if total else "0%",
            )

        # --- Cumulative accuracy vs ground truth ---
        st.divider()
        st.subheader("🎯 Accuracy vs Ground Truth (All Analyzed Tiles)")

        total_compared = 0
        correct = 0
        confusion = {}
        tiles_with_gt = 0

        for tile_name, tile_results in st.session_state.results_cache.items():
            gt_path = os.path.join(GROUND_TRUTH_DIR, f"{tile_name}_post_disaster.json")
            if not os.path.exists(gt_path):
                continue
            tiles_with_gt += 1

            with open(gt_path, "r") as f:
                gt_data = json.load(f)

            gt_lookup = {
                p.get("properties", {}).get("uid", ""): p.get("properties", {}).get("subtype", "unknown")
                for p in gt_data.get("features", {}).get("lng_lat", [])
            }

            for r in tile_results:
                uid = r.get("uid", "")
                ai_damage = r.get("damage", "un-classified")
                gt_damage = gt_lookup.get(uid)
                if gt_damage and gt_damage != "un-classified":
                    total_compared += 1
                    if ai_damage == gt_damage:
                        correct += 1
                    key = (gt_damage, ai_damage)
                    confusion[key] = confusion.get(key, 0) + 1

        if total_compared > 0:
            accuracy = correct / total_compared * 100
            st.metric(
                "Overall Accuracy",
                f"{accuracy:.1f}%",
                delta=f"{correct}/{total_compared} correct across {tiles_with_gt} tile(s)",
            )
            with st.expander("Confusion Details"):
                for (gt, ai), count in sorted(confusion.items(), key=lambda x: -x[1]):
                    match = "✅" if gt == ai else "❌"
                    st.write(f"{match} Ground Truth: **{gt}** → AI: **{ai}** ({count}x)")
        else:
            st.info("No ground truth available for the analyzed tiles.")

        # --- Per-tile building details (scoped to selected tile for manageability) ---
        st.divider()
        st.subheader(f"🏠 Building Details — {selected_name}")
        st.caption("Showing buildings for the tile selected on the Map tab. Switch tiles there to see others.")

        tile_results = st.session_state.results_cache.get(selected_name, [])
        if not tile_results:
            st.info("Selected tile has not been analyzed yet.")
        else:
            for r in tile_results:
                damage = r.get("damage", "unknown")
                color_hex = {
                    "no-damage": "🟩",
                    "minor-damage": "🟨",
                    "destroyed": "🟥",
                    "un-classified": "⬜",
                }.get(damage, "⬜")

                conf_val = r.get("confidence", 0)
                try:
                    conf_text = f"{float(conf_val):.0%}"
                except Exception:
                    conf_text = str(conf_val)

                with st.expander(f"{color_hex} {r.get('uid', '?')[:12]}... — {damage} ({conf_text})"):
                    st.write(r.get("description", "No description available."))

        # --- Download everything ---
        st.divider()
        st.download_button(
            "💾 Download ALL AI Predictions (JSON)",
            data=json.dumps(st.session_state.results_cache, indent=2),
            file_name="all_ai_predictions.json",
            mime="application/json",
        )

# =============================================================================
# SIDEBAR: AI CHATBOT
# =============================================================================
@st.fragment
def render_chat_sidebar(selected_name, results_for_chat):
    st.header("💬 Ask About Results")

    think_fast = st.toggle(
        "⚡ Think Faster",
        value=False,
        help="Uses a faster model with shorter responses.",
    )

    with st.expander("Suggested chatbot questions (Santa Rosa wildfire)", expanded=False):
        if CHATBOT_QUESTION_TYPES.strip():
            st.markdown(CHATBOT_QUESTION_TYPES)
        else:
            st.info("Could not load docs/docs/chatbot_questions.md")

    if not results_for_chat:
        st.info("Run an analysis first to enable the chatbot. It can answer questions about the damage results.")
        return

    total_chat = len(results_for_chat)
    destroyed_chat = sum(1 for r in results_for_chat if r.get("damage") == "destroyed")
    minor_chat = sum(1 for r in results_for_chat if r.get("damage") == "minor-damage")
    no_damage_chat = sum(1 for r in results_for_chat if r.get("damage") == "no-damage")
    unclassified_chat = sum(1 for r in results_for_chat if r.get("damage") == "un-classified")

    building_details = ""
    for r in results_for_chat[:100]:
        conf_value = r.get("confidence", 0)
        try:
            conf_text = f"{float(conf_value):.0%}"
        except Exception:
            conf_text = str(conf_value)
        building_details += (
            f"  - UID: {r.get('uid', '?')}, "
            f"Damage: {r.get('damage', '?')}, "
            f"Confidence: {conf_text}, "
            f"Notes: {r.get('description', 'N/A')}\n"
        )
    if len(results_for_chat) > 100:
        building_details += f"  ... and {len(results_for_chat) - 100} more buildings\n"

    system_context = f"""You are a disaster damage assessment assistant for the Santa Rosa wildfire project.
You have access to AI classified building damage data for satellite tile: {selected_name}

DAMAGE SUMMARY:
- Total buildings analyzed: {total_chat}
- No damage: {no_damage_chat} ({no_damage_chat/total_chat*100:.1f}%)
- Minor damage: {minor_chat} ({minor_chat/total_chat*100:.1f}%)
- Destroyed: {destroyed_chat} ({destroyed_chat/total_chat*100:.1f}%)
- Un-classified (API failures): {unclassified_chat} ({unclassified_chat/total_chat*100:.1f}%)

INDIVIDUAL BUILDING DATA (up to 100 shown):
{building_details}

SUPPORTED CHATBOT QUESTION TYPES (Person 6):
{CHATBOT_QUESTION_TYPES}

RESPONSE FORMAT:
1) Answer
2) Evidence
3) Notes

RULES:
- If asked for counts, include both count and percentage when possible.
- If asked about worst affected areas, explain which damage categories dominate based on the data you have.
- For uncertainty questions, treat confidence below 0.60 as low confidence.
- If asked about a specific building, look up its UID in the data above.
- Do not invent building UIDs or numbers not present in the provided data.
- Keep answers focused and helpful.
"""

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_question = st.chat_input("Ask about the damage results...")

    if user_question:
        st.session_state.chat_messages.append({"role": "user", "content": user_question})

        with st.chat_message("user"):
            st.write(user_question)

        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY is not set in your environment.")

            client = genai.Client(api_key=api_key)

            gemini_contents = [system_context]
            for msg in st.session_state.chat_messages:
                gemini_contents.append(f"{msg['role'].upper()}: {msg['content']}")

            model_name = FAST_CHAT_MODEL if think_fast else DEFAULT_CHAT_MODEL

            with st.chat_message("assistant"):
                thinking_placeholder = st.empty()
                thinking_placeholder.markdown(
                    """
                    <div class="thinking-bubbles">
                        <span></span><span></span><span></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=gemini_contents,
                )

                assistant_reply = response.text if getattr(response, "text", None) else "No response returned."
                thinking_placeholder.empty()
                st.write(assistant_reply)

            st.session_state.chat_messages.append(
                {"role": "assistant", "content": assistant_reply}
            )

        except Exception as e:
            error_msg = f"Chat error: {e}"
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": error_msg}
            )
            with st.chat_message("assistant"):
                st.error(error_msg)

    if st.session_state.chat_messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()

with st.sidebar:
    results_for_chat = st.session_state.results_cache.get(selected_name)
    render_chat_sidebar(selected_name, results_for_chat)

# =============================================================================
# TAB 3: UPLOAD IMAGES
# =============================================================================
with tab_upload:
    st.header("📤 Upload Your Own Disaster Tile")

    # Separate session state so uploaded tiles don't pollute the demo cache
    if "uploaded_results" not in st.session_state:
        st.session_state.uploaded_results = None
    if "uploaded_paths" not in st.session_state:
        st.session_state.uploaded_paths = None

    pre_image = st.file_uploader(
        "Pre Disaster Image",
        type=["png", "jpg", "jpeg"],
        key="custom_pre_image",
    )
    post_image = st.file_uploader(
        "Post Disaster Image",
        type=["png", "jpg", "jpeg"],
        key="custom_post_image",
    )
    geojson_file = st.file_uploader(
        "Building Polygon JSON (xView2/FEMA format)",
        type=["json", "geojson"],
        key="custom_geojson",
        help='Must contain `features.lng_lat[]` with `wkt` strings and `properties.uid`.',
    )

    # --- Image preview ---
    if pre_image and post_image:
        col1, col2 = st.columns(2)
        with col1:
            st.image(pre_image, caption="Pre Disaster", use_container_width=True)
        with col2:
            st.image(post_image, caption="Post Disaster", use_container_width=True)

    # --- Validate GeoJSON shape early so the user gets a helpful error ---
    valid_geojson = False
    uploaded_building_count = 0
    if geojson_file is not None:
        try:
            geojson_file.seek(0)
            preview_data = json.loads(geojson_file.read().decode("utf-8"))
            geojson_file.seek(0)  # reset for later save
            uploaded_polygons = preview_data.get("features", {}).get("lng_lat", [])
            uploaded_building_count = len(uploaded_polygons)
            if uploaded_building_count > 0:
                valid_geojson = True
                st.info(f"📍 {uploaded_building_count} building polygons found in uploaded JSON")
            else:
                st.error(
                    "Uploaded JSON has no polygons under `features.lng_lat`. "
                    "Make sure it follows the xView2/FEMA label format."
                )
        except Exception as e:
            st.error(f"Could not parse uploaded JSON: {e}")

    # --- Analysis controls ---
    if pre_image and post_image and valid_geojson:
        with st.form("upload_analysis_form"):
            upload_batch_size = st.selectbox(
                "Batch size (buildings per API call):",
                [25, 50, 85, 170],
                index=2,
                help="Larger = fewer API calls. 85 recommended for Pro.",
                key="upload_batch_size",
            )
            run_upload_btn = st.form_submit_button(
                "🔍 Analyze Uploaded Tile", type="primary"
            )

        if run_upload_btn:
            upload_dir = Path("uploaded_user_images")
            upload_dir.mkdir(exist_ok=True)

            # Use original extensions so PIL can open jpg/jpeg correctly
            pre_ext = Path(pre_image.name).suffix.lower() or ".png"
            post_ext = Path(post_image.name).suffix.lower() or ".png"

            pre_path = upload_dir / f"user_pre{pre_ext}"
            post_path = upload_dir / f"user_post{post_ext}"
            label_path = upload_dir / "user_labels.json"

            with open(pre_path, "wb") as f:
                f.write(pre_image.getbuffer())
            with open(post_path, "wb") as f:
                f.write(post_image.getbuffer())
            with open(label_path, "wb") as f:
                f.write(geojson_file.getbuffer())

            # If the input wasn't PNG, normalize to PNG since the detector saves PNG bytes anyway.
            # analyze_tile uses PIL.Image.open which handles jpg fine, so this is just defensive.
            try:
                with Image.open(pre_path) as im:
                    if pre_ext != ".png":
                        png_path = upload_dir / "user_pre.png"
                        im.convert("RGB").save(png_path, format="PNG")
                        pre_path = png_path
                with Image.open(post_path) as im:
                    if post_ext != ".png":
                        png_path = upload_dir / "user_post.png"
                        im.convert("RGB").save(png_path, format="PNG")
                        post_path = png_path
            except Exception as e:
                st.error(f"Could not read uploaded images: {e}")
                st.stop()

            status_text = st.empty()
            progress_bar = st.progress(0)

            def _upload_progress(batch_num, total_batches):
                progress_bar.progress(batch_num / total_batches)
                status_text.text(f"Classifying batch {batch_num}/{total_batches}...")

            max_retries = 3
            results = None
            for attempt in range(max_retries):
                try:
                    status_text.text(
                        f"Running backend (attempt {attempt + 1}/{max_retries})..."
                    )
                    detector = DamageDetector()
                    results = detector.analyze_tile(
                        str(pre_path),
                        str(post_path),
                        str(label_path),
                        batch_size=upload_batch_size,
                        progress_callback=_upload_progress,
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait = 60 * (attempt + 1)
                        status_text.text(
                            f"⚠️ Failed, retrying in {wait}s ({attempt + 1}/{max_retries})..."
                        )
                        time.sleep(wait)
                    else:
                        st.error(f"Analysis failed after {max_retries} attempts: {e}")

            if results is not None:
                progress_bar.progress(1.0)
                status_text.text(f"✅ {len(results)} buildings classified")
                st.session_state.uploaded_results = results
                st.session_state.uploaded_paths = {
                    "pre": str(pre_path),
                    "post": str(post_path),
                    "label": str(label_path),
                }

    # --- Results display (persists across reruns via session state) ---
    if st.session_state.uploaded_results and st.session_state.uploaded_paths:
        results = st.session_state.uploaded_results
        paths = st.session_state.uploaded_paths

        st.divider()
        st.subheader("📊 Results")

        total = len(results)
        destroyed = sum(1 for r in results if r.get("damage") == "destroyed")
        minor = sum(1 for r in results if r.get("damage") == "minor-damage")
        no_damage = sum(1 for r in results if r.get("damage") == "no-damage")
        unclassified = sum(1 for r in results if r.get("damage") == "un-classified")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Buildings", total)
        c2.metric(
            "No Damage",
            no_damage,
            delta=f"{no_damage/total*100:.0f}%" if total else "0%",
            delta_color="normal",
        )
        c3.metric(
            "Minor Damage",
            minor,
            delta=f"{minor/total*100:.0f}%" if total else "0%",
            delta_color="off",
        )
        c4.metric(
            "Destroyed",
            destroyed,
            delta=f"{destroyed/total*100:.0f}%" if total else "0%",
            delta_color="inverse",
        )
        if unclassified > 0:
            st.metric(
                "Un-classified",
                unclassified,
                delta=f"{unclassified/total*100:.0f}%" if total else "0%",
            )

        # --- Interactive damage map ---
        st.divider()
        st.subheader("🗺️ Damage Assessment Map")

        upload_bounds = get_bounds_from_label(paths["label"])
        if upload_bounds:
            try:
                with open(paths["label"], "r") as f:
                    upload_label_data = json.load(f)
            except Exception as e:
                st.warning(f"Could not reload uploaded label JSON: {e}")
                upload_label_data = {"features": {"lng_lat": []}}

            uid_to_damage = {
                r.get("uid", ""): {
                    "damage": r.get("damage", "un-classified"),
                    "confidence": r.get("confidence", 0),
                    "description": r.get("description", ""),
                }
                for r in results
            }

            features_for_map = []
            poly_lats = []
            poly_lngs = []
            for poly_data in upload_label_data.get("features", {}).get("lng_lat", []):
                wkt_str = poly_data.get("wkt", "")
                uid = poly_data.get("properties", {}).get("uid", "")
                try:
                    geom = wkt_loads(wkt_str)
                    coords = list(geom.exterior.coords)
                    poly_lngs.extend(c[0] for c in coords)
                    poly_lats.extend(c[1] for c in coords)
                    ai = uid_to_damage.get(
                        uid,
                        {
                            "damage": "un-classified",
                            "confidence": 0,
                            "description": "Not classified",
                        },
                    )
                    features_for_map.append({"geom": geom, "uid": uid, **ai})
                except Exception:
                    continue

            if not features_for_map:
                st.warning("No valid polygons to display on the map.")
            else:
                upload_bg_mode = st.radio(
                    "Background layer",
                    ["Pre Disaster", "Post Disaster"],
                    horizontal=True,
                    key="upload_map_bg_mode",
                )

                south, west = upload_bounds[0]
                north, east = upload_bounds[1]
                center_lat = (south + north) / 2
                center_lng = (west + east) / 2

                m = folium.Map(
                    location=[center_lat, center_lng],
                    zoom_start=18,
                    tiles=None,
                )
                folium.TileLayer(
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attr="Esri World Imagery",
                    name="Esri Satellite",
                    overlay=False,
                    control=False,
                ).add_to(m)

                bg_image_path = paths["pre"] if upload_bg_mode == "Pre Disaster" else paths["post"]
                try:
                    image_url = image_to_data_url(bg_image_path)
                    ImageOverlay(
                        image=image_url,
                        bounds=upload_bounds,
                        opacity=0.72,
                        interactive=False,
                        cross_origin=False,
                        zindex=1,
                    ).add_to(m)
                except Exception as e:
                    st.warning(f"Could not render background overlay: {e}")

                for feat in features_for_map:
                    damage = feat["damage"]
                    color = DAMAGE_COLOR.get(damage, "#808080")
                    fill_opacity = DAMAGE_FILL_OPACITY.get(damage, 0.3)
                    poly_coords = [(lat, lng) for lng, lat in feat["geom"].exterior.coords]

                    conf = feat.get("confidence", 0)
                    if isinstance(conf, (int, float)):
                        conf_str = f"{conf:.0%}" if conf <= 1 else f"{conf}%"
                    else:
                        conf_str = str(conf)

                    tooltip_text = f"{damage} ({conf_str}) - {feat['uid'][:8]}"
                    folium.Polygon(
                        locations=poly_coords,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=fill_opacity,
                        weight=2,
                        tooltip=tooltip_text,
                    ).add_to(m)

                m.fit_bounds(upload_bounds)
                st_folium(
                    m,
                    width=1400,
                    height=650,
                    returned_objects=[],
                    key=f"upload_damage_map_{upload_bg_mode}",
                )

                st.markdown(
                    """
                    | Color | Damage Level |
                    |-------|-------------|
                    | 🟩 | No Damage |
                    | 🟨 | Minor Damage |
                    | 🟥 | Destroyed |
                    | ⬜ | Un-classified |
                    """
                )
        else:
            st.warning(
                "Could not derive geographic bounds from the uploaded JSON, "
                "so the interactive damage map can't be rendered."
            )

        # --- Per-building details ---
        st.divider()
        st.subheader("🏠 Building Details")
        for r in results:
            damage = r.get("damage", "unknown")
            color_hex = {
                "no-damage": "🟩",
                "minor-damage": "🟨",
                "destroyed": "🟥",
                "un-classified": "⬜",
            }.get(damage, "⬜")

            conf_val = r.get("confidence", 0)
            try:
                conf_text = f"{float(conf_val):.0%}"
            except Exception:
                conf_text = str(conf_val)

            with st.expander(
                f"{color_hex} {r.get('uid', '?')[:12]}... — {damage} ({conf_text})"
            ):
                st.write(r.get("description", "No description available."))

        # --- Download + clear ---
        st.divider()
        col_dl, col_clear = st.columns(2)
        with col_dl:
            st.download_button(
                "💾 Download Results (JSON)",
                data=json.dumps(results, indent=2),
                file_name="uploaded_tile_predictions.json",
                mime="application/json",
            )
        with col_clear:
            if st.button("🗑️ Clear Uploaded Results"):
                st.session_state.uploaded_results = None
                st.session_state.uploaded_paths = None
                st.rerun()

    elif not (pre_image and post_image and valid_geojson):
        st.info(
            "Upload a pre image, post image, and a building polygon JSON to enable analysis."
        )
# =============================================================================
# NO RESULTS STATE
# =============================================================================
if not results and selected_name not in st.session_state.results_cache:
    st.info("👆 Select a tile and click **Analyze Damage with AI** to get started.")
elif not results:
    st.warning("AI returned no results for this image pair.")
