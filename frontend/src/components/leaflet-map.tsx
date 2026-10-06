"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { Circle, MapContainer, TileLayer, Tooltip } from "react-leaflet";

// Show an approximate area (a circle) rather than a pin, so the exact address isn't broadcast.
export default function LeafletMap({ lat, lng, label }: { lat: number; lng: number; label: string }) {
  const center = L.latLng(lat, lng);
  return (
    <MapContainer center={center} zoom={15} scrollWheelZoom={false} className="h-64 w-full rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Circle center={center} radius={250} pathOptions={{ color: "#15803d", fillOpacity: 0.15 }}>
        <Tooltip>{label} (approximate area)</Tooltip>
      </Circle>
    </MapContainer>
  );
}
