import streamlit as st
import json
import os
import glob
import folium
from pathlib import Path

from google import genai
from google.genai import types
from shapely.wkt import loads as wkt_loads
from shapely.geometry import mapping
from streamlit_folium import folium_static
from ai_damage_detector import DamageDetector

# =============================================================================
# LOAD PERSON 6 CHATBOT QUESTION TYPES (from docs)
# =============================================================================
QUESTIONS_PATH = Path("docs/docs/chatbot_questions.md")
try:
    CHATBOT_QUESTION_TYPES = QUESTIONS_PATH.read_text(encoding="utf-8") if QUESTIONS_PATH.exists() else ""
except Exception:
    CHATBOT_QUESTION_TYPES = ""

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
st.title("🔥 Santa Rosa Wildfire: Disaster Damage Assessment")
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
FEMA_DIR = "./data/santa_rosa_demo/fema"                 # Stripped JSONs (no damage labels)
GROUND_TRUTH_DIR = "./data/santa_rosa_demo/ground_truth" # Original JSONs (with damage labels)

# Find all post-disaster images and match them with pre images + label files
post_images = sorted(glob.glob(os.path.join(POST_DIR, "*_post_disaster.png")))
available_pairs = []

for post_path in post_images:
    filename = os.path.basename(post_path)
    base_name = filename.replace("_post_disaster.png", "")
    pre_path = os.path.join(PRE_DIR, f"{base_name}_pre_disaster.png")
    label_path = os.path.join(FEMA_DIR, f"{base_name}_post_disaster.json")
    if os.path.exists(pre_path) and os.path.exists(label_path):
        available_pairs.append({
            "name": base_name,
            "pre": pre_path,
            "post": post_path,
            "label": label_path,
        })

if not available_pairs:
    st.error("⚠️ No valid image pairs with labels found. Ensure data/santa_rosa_demo/ has pre/, post/, and fema/ folders.")
    st.stop()

selected_name = st.selectbox(
    f"Choose an image pair ({len(available_pairs)} available):",
    [p["name"] for p in available_pairs],
)
selected_pair = next(p for p in available_pairs if p["name"] == selected_name)

col_pre, col_post = st.columns(2)
with col_pre:
    st.image(selected_pair["pre"], caption="PRE-disaster", use_column_width=True)
with col_post:
    st.image(selected_pair["post"], caption="POST-disaster", use_column_width=True)

with open(selected_pair["label"], "r") as f:
    label_data = json.load(f)
building_count = len(label_data.get("features", {}).get("lng_lat", []))
st.info(f"📍 {building_count} building polygons found in label file")

# =============================================================================
# SECTION 2: AI ANALYSIS TRIGGER
# =============================================================================
st.divider()

if "results_cache" not in st.session_state:
    st.session_state.results_cache = {}

with st.form("analysis_form"):
    batch_size = st.selectbox(
        "Batch size (buildings per API call):",
        [25, 50, 85, 170],
        index=2,
        help="Larger = fewer API calls. 85 recommended for Pro."
    )
    analyze_btn = st.form_submit_button("🔍 Analyze Damage with AI", type="primary")

if analyze_btn:
    progress_text = st.empty()
    progress_bar = st.progress(0)

    try:
        detector = DamageDetector()
        progress_text.text("Initializing AI...")

        results = detector.analyze_tile(
            selected_pair["pre"],
            selected_pair["post"],
            selected_pair["label"],
            batch_size=batch_size,
        )

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
results = st.session_state.results_cache.get(selected_name)

if results:
    st.divider()
    st.subheader("🗺️ Damage Assessment Map")

    uid_to_damage = {}
    for r in results:
        uid_to_damage[r.get("uid", "")] = {
            "damage": r.get("damage", "un-classified"),
            "confidence": r.get("confidence", 0),
            "description": r.get("description", ""),
        }

    polygons = label_data.get("features", {}).get("lng_lat", [])
    all_lats = []
    all_lngs = []
    features_for_map = []

    for poly_data in polygons:
        wkt_str = poly_data.get("wkt", "")
        uid = poly_data.get("properties", {}).get("uid", "")

        try:
            geom = wkt_loads(wkt_str)
            coords = list(geom.exterior.coords)
            lngs = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            all_lngs.extend(lngs)
            all_lats.extend(lats)

            ai_result = uid_to_damage.get(uid, {
                "damage": "un-classified",
                "confidence": 0,
                "description": "Not classified",
            })

            features_for_map.append({
                "geom": geom,
                "uid": uid,
                "damage": ai_result["damage"],
                "confidence": ai_result["confidence"],
                "description": ai_result["description"],
            })
        except Exception:
            continue

    if not features_for_map:
        st.warning("No valid polygons to display")
        st.stop()

    center_lat = sum(all_lats) / len(all_lats)
    center_lng = sum(all_lngs) / len(all_lngs)

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=17,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
    )

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

    m.fit_bounds([[min(all_lats), min(all_lngs)], [max(all_lats), max(all_lngs)]])
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
    gt_path = os.path.join(GROUND_TRUTH_DIR, f"{selected_name}_post_disaster.json")
    if os.path.exists(gt_path):
        st.divider()
        st.subheader("🎯 Accuracy vs Ground Truth")

        with open(gt_path, "r") as f:
            gt_data = json.load(f)

        gt_polygons = gt_data.get("features", {}).get("lng_lat", [])
        gt_lookup = {}
        for p in gt_polygons:
            uid = p.get("properties", {}).get("uid", "")
            subtype = p.get("properties", {}).get("subtype", "unknown")
            gt_lookup[uid] = subtype

        correct = 0
        total_compared = 0
        confusion = {}

        for r in results:
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
            st.metric("Overall Accuracy", f"{accuracy:.1f}%", delta=f"{correct}/{total_compared} correct")

            with st.expander("Confusion Details"):
                for (gt, ai), count in sorted(confusion.items(), key=lambda x: -x[1]):
                    match = "✅" if gt == ai else "❌"
                    st.write(f"{match} Ground Truth: **{gt}** → AI: **{ai}** ({count}x)")
        else:
            st.info("No comparable ground truth labels found for this tile.")

    # ==========================================================================
    # SECTION 7: PER-BUILDING DETAILS
    # ==========================================================================
    st.divider()
    st.subheader("🏠 Building Details")
    for r in results:
        damage = r.get("damage", "unknown")
        color_hex = {
            "no-damage": "🟩",
            "minor-damage": "🟨",
            "destroyed": "🟥",
        }.get(damage, "⬜")

        conf_val = r.get("confidence", 0)
        try:
            conf_text = f"{float(conf_val):.0%}"
        except Exception:
            conf_text = str(conf_val)

        with st.expander(f"{color_hex} {r.get('uid', '?')[:12]}... — {damage} ({conf_text})"):
            st.write(r.get("description", "No description available."))

    # ==========================================================================
    # SECTION 8: JSON EXPORT
    # ==========================================================================
    st.divider()
    st.download_button(
        "💾 Download AI Predictions (JSON)",
        data=json.dumps(results, indent=2),
        file_name=f"{selected_name}_ai_predictions.json",
        mime="application/json",
    )

# =============================================================================
# SIDEBAR: AI CHATBOT
# =============================================================================
with st.sidebar:
    st.header("💬 Ask About Results")

    # Show suggested questions (Person 6 doc) to guide users
    with st.expander("Suggested chatbot questions (Santa Rosa wildfire)", expanded=False):
        if CHATBOT_QUESTION_TYPES.strip():
            st.markdown(CHATBOT_QUESTION_TYPES)
        else:
            st.info("Could not load docs/docs/chatbot_questions.md")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    results_for_chat = st.session_state.results_cache.get(selected_name)

    if results_for_chat:
        total_chat = len(results_for_chat)
        destroyed_chat = sum(1 for r in results_for_chat if r.get("damage") == "destroyed")
        minor_chat = sum(1 for r in results_for_chat if r.get("damage") == "minor-damage")
        no_damage_chat = sum(1 for r in results_for_chat if r.get("damage") == "no-damage")
        unclassified_chat = sum(1 for r in results_for_chat if r.get("damage") == "un-classified")

        building_details = ""
        for r in results_for_chat[:100]:
            building_details += (
                f"  - UID: {r.get('uid', '?')}, "
                f"Damage: {r.get('damage', '?')}, "
                f"Confidence: {r.get('confidence', 0):.0%}, "
                f"Notes: {r.get('description', 'N/A')}\n"
            )
        if len(results_for_chat) > 100:
            building_details += f"  ... and {len(results_for_chat) - 100} more buildings\n"

        # --- UPDATED PROMPT: includes your question types + rules + format ---
        system_context = f"""You are a disaster damage assessment assistant for the Santa Rosa wildfire project.
You have access to AI-classified building damage data for satellite tile: {selected_name}

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

RESPONSE FORMAT (always follow):
1) Answer (1–2 sentences)
2) Evidence (counts / percentages / specific UIDs from the data)
3) Notes (limitations, low confidence, un-classified API failures)

RULES:
- If asked for counts, include both count and percentage when possible.
- If asked "worst affected areas", explain which damage categories dominate based on the data you have.
- For uncertainty questions, treat confidence below 0.60 as low confidence and report how many match.
- If asked about a specific building, look up its UID in the data above.
- Do NOT invent building UIDs or numbers not present in the provided data.
- Keep answers focused and helpful.
"""

        # Display chat history
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
                client = genai.Client(api_key=api_key)

                gemini_contents = [system_context]
                for msg in st.session_state.chat_messages:
                    gemini_contents.append(f"{msg['role'].upper()}: {msg['content']}")

                response = client.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=gemini_contents,
                )

                assistant_reply = response.text
                st.session_state.chat_messages.append({"role": "assistant", "content": assistant_reply})
                with st.chat_message("assistant"):
                    st.write(assistant_reply)

            except Exception as e:
                error_msg = f"Chat error: {e}"
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                with st.chat_message("assistant"):
                    st.error(error_msg)

        if st.session_state.chat_messages:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_messages = []
                st.rerun()
    else:
        st.info("Run an analysis first to enable the chatbot. It can answer questions about the damage results.")

# =============================================================================
# NO RESULTS STATE
# =============================================================================
if not results and selected_name not in st.session_state.results_cache:
    st.info("👆 Select an image pair and click **Analyze Damage with AI** to get started.")
elif not results:
    st.warning("AI returned no results for this image pair.")
