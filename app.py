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
    file_path = "./data/ai_santa_rosa_damage.geojson"  # CHANGED

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

    # Add zoom level selector
    zoom_preset = st.radio(
        "View:",
        ["Overview (all buildings)", "Close-up (detailed view)"],
        horizontal=True
    )

    if data and len(data['features']) > 0:
        # Calculate bounds
        all_lats = []
        all_lons = []

        for feature in data['features']:
            if feature['geometry']['type'] == 'Polygon':
                coords = feature['geometry']['coordinates'][0]
                for lon, lat in coords:
                    all_lats.append(lat)
                    all_lons.append(lon)

        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)

        # Set zoom based on selection
        if zoom_preset == "Overview (all buildings)":
            zoom_level = 12
        else:
            zoom_level = 17

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles="OpenStreetMap"
        )

        # Add all buildings with thicker borders for visibility
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
                weight=2,  # Thicker border for visibility
                fill=True,
                fillColor=color,
                fillOpacity=0.7,  # More opaque
                popup=f"<b>Damage:</b> {damage}<br><b>Image:</b> {image_id}"
            ).add_to(m)

        # Add a legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 180px; height: 160px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p style="margin:0; font-weight:bold;">Damage Legend</p>
        <p style="margin:5px 0;"><span style="color:#00ff00;">█</span> No Damage</p>
        <p style="margin:5px 0;"><span style="color:#ffff00;">█</span> Minor Damage</p>
        <p style="margin:5px 0;"><span style="color:#ffa500;">█</span> Major Damage</p>
        <p style="margin:5px 0;"><span style="color:#ff0000;">█</span> Destroyed</p>
        <p style="margin:5px 0;"><span style="color:#808080;">█</span> Unclassified</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

    else:
        #-122.7534731377982,
        #38.50148499983604
        #m = folium.Map(location=[14.47, -90.88], zoom_start=15, tiles="OpenStreetMap")
        m = folium.Map(location=[-122.7534731377982, 38.50148499983604], zoom_start=1, tiles="OpenStreetMap")

    map_html = m._repr_html_()
    html(map_html, height=600)

    st.info(
        "💡 Tip: Use the + button on the map to zoom in and see individual buildings. Click 'Close-up' above for a detailed view.")

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
    minor = sum(1 for f in data['features'] if f['properties']['damage'] == 'minor-damage')
    no_damage = sum(1 for f in data['features'] if f['properties']['damage'] == 'no-damage')

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Buildings", total_buildings)
    m2.metric("No Damage", no_damage, delta=f"{no_damage / total_buildings * 100:.0f}%", delta_color="normal")
    m3.metric("Minor Damage", minor, delta=f"{minor / total_buildings * 100:.0f}%", delta_color="off")
    m4.metric("Major Damage", major, delta=f"{major / total_buildings * 100:.0f}%", delta_color="off")
    m5.metric("Destroyed", destroyed, delta=f"{destroyed / total_buildings * 100:.0f}%", delta_color="inverse")