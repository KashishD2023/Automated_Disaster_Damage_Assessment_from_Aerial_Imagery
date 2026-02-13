import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";

/*
  Put your images here:

  Option A (recommended): put them in /public/icons/
    /public/icons/home-marker.png
    /public/icons/fire-marker.png

  Then the iconUrl below works as is.

  Option B: import from src (uncomment imports) and set iconUrl to the imported value.
*/
// import homeMarker from "./assets/home-marker.png";
// import fireMarker from "./assets/fire-marker.png";

const homeMarkerIcon = new L.Icon({
  iconUrl: "/icons/home-marker.png", // or homeMarker
  iconSize: [44, 44],
  iconAnchor: [22, 44],
  popupAnchor: [0, -38],
});

const fireAreaIcon = new L.Icon({
  iconUrl: "/icons/fire-marker.png", // or fireMarker
  iconSize: [44, 44],
  iconAnchor: [22, 44],
  popupAnchor: [0, -38],
});

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (!center) return;
    map.setView(center, Math.max(map.getZoom(), 13), { animate: true });
  }, [center, map]);
  return null;
}

function MapView() {
  const [viewMode, setViewMode] = useState("pre");
  const [selectedTile, setSelectedTile] = useState(null);

  const [userLoc, setUserLoc] = useState(null);
  const [geoError, setGeoError] = useState("");

  const [messages, setMessages] = useState([
    { id: 1, role: "system", text: "Chat is ready. Type a message below." },
  ]);
  const [draft, setDraft] = useState("");
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const tile = useMemo(
    () => ({
      tile_id: "Addison",
      lat: 32.9618,
      lon: -96.8292,
      pre: "/demo_images/tile1_pre.jpg",
      post: "/demo_images/tile1_post.jpg",
    }),
    []
  );

  const activeTile = selectedTile ? tile : null;
  const imagePath =
    activeTile && viewMode === "pre" ? activeTile.pre : activeTile?.post;

  const requestLocation = () => {
    setGeoError("");
    if (!navigator.geolocation) {
      setGeoError("Geolocation is not supported in this browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLoc([pos.coords.latitude, pos.coords.longitude]);
      },
      (err) => setGeoError(err.message || "Could not get location."),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
  };

  useEffect(() => {
    requestLocation();
  }, []);

  const mapCenter = userLoc || [tile.lat, tile.lon];

  const sendMessage = () => {
    const text = draft.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { id: Date.now(), role: "you", text }]);
    setDraft("");
  };

  return (
    <div style={{ height: "100vh", width: "100vw", display: "flex" }}>
      {/* Left panel */}
      <div
        style={{
          width: "340px",
          borderRight: "1px solid #ddd",
          fontFamily: "Arial, sans-serif",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ padding: "12px" }}>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
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

            <button
              onClick={requestLocation}
              style={{
                marginLeft: "auto",
                padding: "8px 12px",
                cursor: "pointer",
              }}
              title="Request location permission again"
            >
              My location
            </button>
          </div>

          <div style={{ marginTop: "10px", fontWeight: 700 }}>
            Current view: {viewMode.toUpperCase()}
          </div>

          {geoError ? (
            <div style={{ marginTop: "8px", color: "#b91c1c", fontSize: 12 }}>
              {geoError}
            </div>
          ) : null}

          <div style={{ marginTop: "12px" }}>
            {!activeTile && (
              <div style={{ color: "#555" }}>
                Click the Addison marker to open the preview.
              </div>
            )}

            {activeTile && (
              <>
                <div style={{ marginBottom: "8px" }}>
                  Tile: {activeTile.tile_id}
                </div>

                <img
                  src={imagePath}
                  alt="Tile preview"
                  style={{ width: "100%", height: "auto", display: "block" }}
                />
              </>
            )}
          </div>
        </div>

        {/* Chat box */}
        <div
          style={{
            borderTop: "1px solid #eee",
            padding: "10px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            flex: 1,
            minHeight: 0,
          }}
        >
          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: "auto",
              background: "#fafafa",
              border: "1px solid #eee",
              borderRadius: 8,
              padding: 10,
            }}
          >
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  marginBottom: 8,
                  display: "flex",
                  justifyContent: m.role === "you" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "85%",
                    padding: "8px 10px",
                    borderRadius: 10,
                    background: m.role === "you" ? "#e5e7eb" : "#ffffff",
                    border: "1px solid #e5e7eb",
                    fontSize: 13,
                    lineHeight: 1.35,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {m.text}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage();
              }}
              placeholder="Type a message"
              style={{
                flex: 1,
                padding: "10px",
                borderRadius: 8,
                border: "1px solid #ddd",
                outline: "none",
              }}
            />
            <button
              onClick={sendMessage}
              style={{
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #ddd",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Map */}
      <div style={{ flex: 1 }}>
        <MapContainer
          center={mapCenter}
          zoom={13}
          style={{ height: "100%", width: "100%" }}
        >
          <Recenter center={userLoc} />

          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />

          {/* Fire area marker for Addison */}
          <Marker
            position={[tile.lat, tile.lon]}
            icon={fireAreaIcon}
            eventHandlers={{
              click: () => setSelectedTile(tile.tile_id),
            }}
          >
            <Popup>Fire area: Addison</Popup>
          </Marker>

          {/* Home marker for current location */}
          {userLoc ? (
            <Marker position={userLoc} icon={homeMarkerIcon}>
              <Popup>Home</Popup>
            </Marker>
          ) : null}
        </MapContainer>
      </div>
    </div>
  );
}

export default MapView;