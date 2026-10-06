"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "./ui";

// Leaflet touches `window`, so it is only ever loaded in the browser.
const LeafletMap = dynamic(() => import("./leaflet-map"), {
  ssr: false,
  loading: () => <Skeleton className="h-64 w-full rounded-xl" />,
});

export function PropertyMap({ lat, lng, label }: { lat: number | null; lng: number | null; label: string }) {
  if (lat === null || lng === null) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl bg-slate-100 text-sm text-slate-500">
        Exact location shared after inspection is booked.
      </div>
    );
  }
  return <LeafletMap lat={lat} lng={lng} label={label} />;
}
