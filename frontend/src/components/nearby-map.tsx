"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";

import { formatDistance, PLACE_CATEGORY_LABELS } from "@/lib/format";
import type { NearbyPlace } from "@/lib/types";

import { CATEGORY_COLORS } from "./nearby-colors";

/** Re-fits only when the set of points changes (not on every hover/selection re-render). */
function FitBounds({ pointsKey }: { pointsKey: string }) {
  const map = useMap();
  useEffect(() => {
    const points = pointsKey.split(";").map((pair) => pair.split(",").map(Number) as [number, number]);
    if (points.length > 1) map.fitBounds(L.latLngBounds(points), { padding: [24, 24], maxZoom: 16 });
  }, [map, pointsKey]);
  return null;
}

/** Map of nearby places. Circle markers avoid Leaflet's bundler icon issues and are colour-coded. */
export default function NearbyMap({
  origin,
  originLabel,
  places,
  selectedId,
  onSelect,
}: {
  origin: { latitude: number; longitude: number };
  originLabel: string;
  places: NearbyPlace[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const pointsKey = [origin, ...places].map((p) => `${p.latitude},${p.longitude}`).join(";");
  return (
    <MapContainer
      center={[origin.latitude, origin.longitude]}
      zoom={14}
      scrollWheelZoom={false}
      className="h-72 w-full rounded-xl sm:h-96"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds pointsKey={pointsKey} />
      {/* An area, not a pin: the exact address is only confirmed at inspection. */}
      <Circle
        center={[origin.latitude, origin.longitude]}
        radius={250}
        pathOptions={{ color: "#15803d", fillColor: "#15803d", fillOpacity: 0.18, weight: 2 }}
      >
        <Tooltip permanent direction="top">
          {originLabel}
        </Tooltip>
      </Circle>
      {places.map((p) => (
        <CircleMarker
          key={p.id}
          center={[p.latitude, p.longitude]}
          radius={p.id === selectedId ? 10 : 7}
          eventHandlers={{ click: () => onSelect(p.id) }}
          pathOptions={{
            color: "#ffffff",
            weight: 2,
            fillColor: CATEGORY_COLORS[p.category],
            fillOpacity: p.id === selectedId ? 1 : 0.85,
          }}
        >
          <Popup>
            <strong>{p.name}</strong>
            <br />
            {PLACE_CATEGORY_LABELS[p.category].one} · {formatDistance(p.distance_km)}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
