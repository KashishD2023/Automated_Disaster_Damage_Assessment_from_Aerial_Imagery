import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";

function MapView() {
  return (
    <MapContainer
      center={[32.7767, -96.797]}
      zoom={10}
      style={{ height: "100vh", width: "100%" }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="© OpenStreetMap contributors"
      />
      <Marker position={[32.7767, -96.797]}>
        <Popup>Demo tile</Popup>
      </Marker>
    </MapContainer>
  );
}

export default MapView;
