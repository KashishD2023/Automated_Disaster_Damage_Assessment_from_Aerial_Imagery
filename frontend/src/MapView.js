import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

const markerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FixMapSize() {
  const map = useMap();

  useEffect(() => {
    setTimeout(() => {
      map.invalidateSize();
    }, 200);
  }, [map]);

  return null;
}

function MapView() {
  const [viewMode, setViewMode] = useState("pre");

  const tile = {
    tile_id: "tile_001",
    lat: 32.7767,
    lon: -96.797,
    pre: "/demo_images/tile1_pre.jpg",
    post: "/demo_images/tile1_post.jpg",
  };

  const imagePath = viewMode === "pre" ? tile.pre : tile.post;

  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      <div
        style={{
          padding: "10px",
          display: "flex",
          gap: "10px",
          alignItems: "center",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <button
          onClick={() => setViewMode("pre")}
          style={{
            padding: "8px 12px",
            cursor: "pointer",
            fontWeight: viewMode === "pre" ? "700" : "400",
          }}
        >
          Pre
        </button>

        <button
          onClick={() => setViewMode("post")}
          style={{
            padding: "8px 12px",
            cursor: "pointer",
            fontWeight: viewMode === "post" ? "700" : "400",
          }}
        >
          Post
        </button>

        <div style={{ marginLeft: "10px" }}>
          Current view: {viewMode.toUpperCase()}
        </div>
      </div>

      <MapContainer
        center={[tile.lat, tile.lon]}
        zoom={10}
        style={{ height: "calc(100vh - 52px)", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap contributors"
        />

        <FixMapSize />

        <Marker position={[tile.lat, tile.lon]} icon={markerIcon}>
          <Popup>
            <div style={{ fontFamily: "Arial, sans-serif" }}>
              <div style={{ fontWeight: 700 }}>{tile.tile_id}</div>
              <div style={{ margin: "6px 0" }}>Preview: {viewMode.toUpperCase()}</div>
              <img
                src={imagePath}
                alt="Tile preview"
                style={{ width: "240px", height: "auto", display: "block" }}
              />
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}

export default MapView;
