import streamlit as st
import folium
import json
from streamlit.components.v1 import html

# PAGE CONFIGURATION
st.set_page_config(layout="wide", page_title="Disaster Assessment AI")

# TITLE & HEADER
st.title("🌋 Project Fuego: Guatemala Damage Assessment")
st.markdown("""
**Status:** Connected to VLM Pipeline  
**Disaster:** Volcán de Fuego, Guatemala  
**Data Source:** xView2 / FEMA Labels
""")


# --- 1. LOAD THE MAP DATA ---
@st.cache_data
def load_data():
    file_path = "./data/guatemala_damage.geojson"

    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"⚠️ Could not find {file_path}. Did you run 'convert_to_geojson.py'?")
        return None


data = load_data()

# --- 2. BUILD THE MAP ---
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Aerial Damage Analysis")

    m = folium.Map(location=[14.47, -90.88], zoom_start=15, tiles="OpenStreetMap")

    if data:
        for feature in data['features']:
            coords = feature['geometry']['coordinates']
            color = feature['properties']['color']
            damage = feature['properties']['damage']
            image_id = feature['properties']['image_id']

            if feature['geometry']['type'] == 'Polygon':
                locations = [(lat, lon) for lon, lat in coords[0]]
            else:
                continue

            folium.Polygon(
                locations=locations,
                color='black',
                weight=1,
                fill=True,
                fillColor=color,
                fillOpacity=0.6,
                popup=f"Damage: {damage}<br>Image: {image_id}"
            ).add_to(m)

    # Render as raw HTML instead of using st_folium
    map_html = m._repr_html_()
    html(map_html, height=500)

# --- 3. BUILD THE CHATBOT (Right Column) ---
with col2:
    st.subheader("💬 AI Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about the damage..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = "I am analyzing the map... Based on the current view, I detect several buildings with 'Major Damage' (Orange) near the main road. The red zones indicate total destruction from the lahar flow."

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# --- 4. METRICS / STATS (Bottom) ---
if data:
    st.divider()
    st.subheader("Damage Statistics")
    total_buildings = len(data['features'])
    destroyed = sum(1 for f in data['features'] if f['properties']['damage'] == 'destroyed')
    major = sum(1 for f in data['features'] if f['properties']['damage'] == 'major-damage')

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Buildings Scanned", total_buildings)
    m2.metric("Destroyed", destroyed, delta_color="inverse")
    m3.metric("Major Damage", major, delta_color="inverse")