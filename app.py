import streamlit as st
import json
import os
import glob
from PIL import Image, ImageDraw, ImageFont
from ai_damage_detector import DamageDetector

# PAGE CONFIGURATION
st.set_page_config(layout="wide", page_title="Disaster Assessment AI")

# COLOR MAPPING (RGB tuples for PIL)
DAMAGE_COLOR = {
    "no-damage": (0, 255, 0),
    "minor-damage": (255, 255, 0),
    "major-damage": (255, 165, 0),
    "destroyed": (255, 0, 0),
    "un-classified": (128, 128, 128),
}

DAMAGE_FILL = {
    "no-damage": (0, 255, 0, 60),
    "minor-damage": (255, 255, 0, 60),
    "major-damage": (255, 165, 0, 60),
    "destroyed": (255, 0, 0, 60),
    "un-classified": (128, 128, 128, 60),
}

# TITLE
st.title("🌋 Project Fuego: Disaster Damage Assessment")
st.markdown("**Powered by** Gemini 2.5 Flash | **Data:** xView2 Satellite Imagery")

# --- 1. IMAGE PAIR SELECTION ---
st.subheader("📂 Select Image Pair")

PRE_DIR = "./data/santa_rosa_demo/pre"
POST_DIR = "./data/santa_rosa_demo/post"

post_images = sorted(glob.glob(os.path.join(POST_DIR, "*_post_disaster.png")))
available_pairs = []

for post_path in post_images:
    filename = os.path.basename(post_path)
    base_name = filename.replace("_post_disaster.png", "")
    pre_path = os.path.join(PRE_DIR, f"{base_name}_pre_disaster.png")
    if os.path.exists(pre_path):
        available_pairs.append({"name": base_name, "pre": pre_path, "post": post_path})

if not available_pairs:
    st.error("⚠️ No valid image pairs found in data/santa_rosa_demo/")
    st.stop()

selected_name = st.selectbox(
    f"Choose an image pair ({len(available_pairs)} available):",
    [p["name"] for p in available_pairs],
)
selected_pair = next(p for p in available_pairs if p["name"] == selected_name)

# Show pre/post side by side
col_pre, col_post = st.columns(2)
with col_pre:
    st.image(selected_pair["pre"], caption="PRE-disaster", use_column_width=True)
with col_post:
    st.image(selected_pair["post"], caption="POST-disaster", use_column_width=True)

# --- 2. RUN AI ANALYSIS ---
st.divider()

if "results_cache" not in st.session_state:
    st.session_state.results_cache = {}

analyze_btn = st.button("🔍 Analyze Damage with AI", type="primary", use_container_width=True)

if analyze_btn:
    with st.spinner("🧠 Running Gemini 2.5 Flash analysis... (15-30 seconds)"):
        try:
            detector = DamageDetector()
            predictions = detector.analyze_damage(selected_pair["pre"], selected_pair["post"])
            st.session_state.results_cache[selected_name] = predictions
            st.success(f"✅ Found {len(predictions)} buildings!")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# --- 3. DISPLAY RESULTS ---
predictions = st.session_state.results_cache.get(selected_name)

if predictions:
    st.divider()
    st.subheader("🔎 Damage Analysis")

    # Load post image and draw bboxes
    post_img = Image.open(selected_pair["post"]).convert("RGBA")
    img_w, img_h = post_img.size

    # Create transparent overlay for filled boxes
    overlay = Image.new("RGBA", post_img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Draw on a copy for outlines and labels
    outline_layer = post_img.copy()
    draw = ImageDraw.Draw(outline_layer)

    for pred in predictions:
        bbox = pred.get("bbox", [])
        damage = pred.get("damage", "un-classified")
        confidence = pred.get("confidence", 0)
        building_id = pred.get("building_id", "?")

        if len(bbox) != 4:
            continue

        # bbox is in pixel coords (0-1024 from AI), scale to actual image size
        x1 = int(bbox[0] * img_w / 1024)
        y1 = int(bbox[1] * img_h / 1024)
        x2 = int(bbox[2] * img_w / 1024)
        y2 = int(bbox[3] * img_h / 1024)

        color = DAMAGE_COLOR.get(damage, (128, 128, 128))
        fill = DAMAGE_FILL.get(damage, (128, 128, 128, 60))

        # Filled rectangle on overlay
        overlay_draw.rectangle([x1, y1, x2, y2], fill=fill)

        # Outline on main image
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        # Label
        label = f"#{building_id} {damage} ({confidence:.0%})"
        text_bbox = draw.textbbox((x1, y1 - 16), label)
        draw.rectangle(text_bbox, fill=(0, 0, 0, 200))
        draw.text((x1, y1 - 16), label, fill=color)

    # Composite
    result_img = Image.alpha_composite(outline_layer, overlay).convert("RGB")

    # Show annotated image
    st.image(result_img, caption="AI Damage Assessment", use_column_width=True)

    # --- 4. LEGEND ---
    legend_md = """
    | Color | Damage Level |
    |-------|-------------|
    | 🟩 | No Damage |
    | 🟨 | Minor Damage |
    | 🟧 | Major Damage |
    | 🟥 | Destroyed |
    """
    st.markdown(legend_md)

    # --- 5. STATS ---
    st.divider()
    st.subheader("📊 Damage Statistics")

    total = len(predictions)
    destroyed = sum(1 for p in predictions if p.get("damage") == "destroyed")
    major = sum(1 for p in predictions if p.get("damage") == "major-damage")
    minor = sum(1 for p in predictions if p.get("damage") == "minor-damage")
    no_damage = sum(1 for p in predictions if p.get("damage") == "no-damage")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Buildings", total)
    m2.metric("No Damage", no_damage, delta=f"{no_damage / total * 100:.0f}%" if total else "0%", delta_color="normal")
    m3.metric("Minor Damage", minor, delta=f"{minor / total * 100:.0f}%" if total else "0%", delta_color="off")
    m4.metric("Major Damage", major, delta=f"{major / total * 100:.0f}%" if total else "0%", delta_color="off")
    m5.metric("Destroyed", destroyed, delta=f"{destroyed / total * 100:.0f}%" if total else "0%", delta_color="inverse")

    # --- 6. BUILDING DETAILS ---
    st.divider()
    st.subheader("🏠 Building Details")
    for pred in predictions:
        damage = pred.get("damage", "unknown")
        color_hex = {
            "no-damage": "🟩", "minor-damage": "🟨",
            "major-damage": "🟧", "destroyed": "🟥"
        }.get(damage, "⬜")

        with st.expander(f"{color_hex} Building #{pred.get('building_id', '?')} — {damage} ({pred.get('confidence', 0):.0%})"):
            st.write(pred.get("description", "No description available."))

    # --- 7. EXPORT ---
    st.divider()
    st.download_button(
        "💾 Download Raw Predictions (JSON)",
        data=json.dumps(predictions, indent=2),
        file_name=f"{selected_name}_predictions.json",
        mime="application/json",
    )

elif selected_name not in st.session_state.results_cache:
    st.info("👆 Select an image pair and click **Analyze Damage with AI** to get started.")
else:
    st.warning("AI returned no buildings for this image pair.")