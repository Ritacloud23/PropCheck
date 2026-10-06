"use client";

import { LocateFixed } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { buttonClass } from "@/components/ui";

/** Uses the browser's location (with permission) and reloads /nearby centred on it. */
export function UseMyLocation({ radius }: { radius: string }) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "locating" | "error">("idle");
  const locate = () => {
    if (!("geolocation" in navigator)) {
      setStatus("error");
      return;
    }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        router.push(`/nearby?lat=${latitude.toFixed(5)}&lng=${longitude.toFixed(5)}&radius=${radius}&label=${encodeURIComponent("Your location")}`);
      },
      () => setStatus("error"),
      { enableHighAccuracy: false, timeout: 10000 },
    );
  };
  return (
    <div className="space-y-1">
      <button type="button" onClick={locate} className={buttonClass("secondary", "md", "w-full")} disabled={status === "locating"}>
        <LocateFixed className="size-4" aria-hidden />
        {status === "locating" ? "Finding you…" : "Use my location"}
      </button>
      {status === "error" && <p className="text-xs text-red-700">Couldn&apos;t get your location. Choose a city instead.</p>}
    </div>
  );
}
