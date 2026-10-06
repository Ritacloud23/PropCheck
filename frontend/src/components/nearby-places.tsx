"use client";

import { Clock, Flag, Info, MapPin, Navigation, Phone } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";

import { errorMessage, post } from "@/lib/api";
import { directionsUrl, formatDistance, formatNgPhone, humanize, PLACE_CATEGORY_LABELS } from "@/lib/format";
import type { NearbyPlace, PlaceCategory } from "@/lib/types";
import { cn } from "@/lib/utils";

import { CATEGORY_COLORS } from "./nearby-colors";
import { Alert, Button, Pill, Select, Skeleton, Textarea, buttonClass } from "./ui";

const NearbyMap = dynamic(() => import("./nearby-map"), {
  ssr: false,
  loading: () => <Skeleton className="h-72 w-full rounded-xl sm:h-96" />,
});

export const NEARBY_NOTICE =
  "Nearby information is provided for convenience and may change. Confirm opening hours, availability and directions before travelling.";

const TABS: { key: PlaceCategory | "ALL"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "MARKET", label: "Markets" },
  { key: "RESTAURANT", label: "Restaurants" },
  { key: "CHURCH", label: "Churches" },
  { key: "CLUB", label: "Clubs" },
];

function ReportPlace({
  place,
  reasons,
  loggedIn,
  loginNext,
}: {
  place: NearbyPlace;
  reasons: string[];
  loggedIn: boolean;
  loginNext: string;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (done) return <p className="text-xs font-medium text-green-700">Thanks — a reviewer will check this place.</p>;
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-red-700"
      >
        <Flag className="size-3.5" aria-hidden /> Report incorrect information
      </button>
    );
  }
  if (!loggedIn) {
    return (
      <p className="text-xs text-slate-600">
        <Link href={`/login?next=${encodeURIComponent(loginNext)}`} className="font-semibold text-brand-700 hover:underline">
          Log in
        </Link>{" "}
        to report incorrect information.
      </p>
    );
  }
  const submit = async () => {
    if (!reason) {
      setError("Choose what is wrong.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await post(`/api/nearby-places/${place.id}/report`, { reason, description: details.trim() || null });
      setDone(true);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="w-full space-y-2 rounded-lg bg-slate-50 p-3 ring-1 ring-slate-200">
      <Select value={reason} onChange={(e) => setReason(e.target.value)} aria-label="What is wrong?" className="h-9 text-sm">
        <option value="">What is wrong?</option>
        {reasons.map((r) => (
          <option key={r} value={r}>
            {humanize(r)}
          </option>
        ))}
      </Select>
      <Textarea
        value={details}
        onChange={(e) => setDetails(e.target.value)}
        placeholder="Optional details, e.g. the correct opening hours"
        maxLength={2000}
        className="min-h-14 text-sm"
        aria-label="Details"
      />
      {error && <p className="text-xs font-medium text-red-700">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" variant="danger" loading={busy} onClick={submit}>
          Send report
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function NearbyPlaces({
  places,
  origin,
  originLabel = "This property",
  radiusKm,
  reportReasons,
  loggedIn,
  loginNext,
  directionsFromOrigin = true,
  initialCategory = "ALL",
}: {
  places: NearbyPlace[];
  origin: { latitude: number; longitude: number };
  originLabel?: string;
  radiusKm: number;
  reportReasons: string[];
  loggedIn: boolean;
  loginNext: string;
  directionsFromOrigin?: boolean;
  initialCategory?: PlaceCategory | "ALL";
}) {
  const [tab, setTab] = useState<PlaceCategory | "ALL">(initialCategory);
  const [selected, setSelected] = useState<number | null>(null);
  const visible = tab === "ALL" ? places : places.filter((p) => p.category === tab);
  const count = (key: PlaceCategory | "ALL") => (key === "ALL" ? places.length : places.filter((p) => p.category === key).length);
  const anyDemo = places.some((p) => p.is_demo_data);

  return (
    <div className="space-y-4">
      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Place categories">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium ring-1",
              tab === t.key ? "bg-slate-900 text-white ring-slate-900" : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50",
            )}
          >
            {t.key !== "ALL" && <span className="size-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[t.key] }} aria-hidden />}
            {t.label}
            <span className={cn("text-xs", tab === t.key ? "text-slate-300" : "text-slate-400")}>{count(t.key)}</span>
          </button>
        ))}
      </div>

      <NearbyMap origin={origin} originLabel={originLabel} places={visible} selectedId={selected} onSelect={setSelected} />

      {visible.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-8 text-center text-sm text-slate-600">
          <p className="font-semibold text-slate-900">
            No {tab === "ALL" ? "places" : PLACE_CATEGORY_LABELS[tab].many.toLowerCase()} found within {radiusKm} km
          </p>
          <p className="mt-1">We&apos;re still adding places in this area. Try another category or a wider search on the nearby page.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-xl bg-white ring-1 ring-slate-200" aria-label="Nearby places">
          {visible.map((p) => (
            <li
              key={p.id}
              className={cn("space-y-2 px-4 py-3 transition-colors", selected === p.id && "bg-brand-50")}
              onMouseEnter={() => setSelected(p.id)}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-semibold text-slate-900">{p.name}</p>
                  <p className="flex flex-wrap items-center gap-x-2 text-sm text-slate-600">
                    <span className="inline-flex items-center gap-1">
                      <span className="size-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[p.category] }} aria-hidden />
                      {PLACE_CATEGORY_LABELS[p.category].one}
                    </span>
                    <span aria-hidden>·</span>
                    <span className="font-medium text-slate-900" data-testid="distance">
                      {formatDistance(p.distance_km)} away
                    </span>
                    {p.is_demo_data && <Pill className="py-0">Demo data</Pill>}
                  </p>
                </div>
                <a
                  href={directionsUrl(p, directionsFromOrigin ? origin : null)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClass("secondary", "sm")}
                >
                  <Navigation className="size-4" aria-hidden /> Get directions
                </a>
              </div>
              <div className="grid gap-1 text-sm text-slate-600 sm:grid-cols-2">
                <p className="flex items-start gap-1.5">
                  <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden />
                  <span>
                    {p.address ?? p.area ?? p.city}
                    <span className="block text-xs text-slate-400">
                      {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                    </span>
                  </span>
                </p>
                {p.opening_hours && (
                  <p className="flex items-start gap-1.5">
                    <Clock className="mt-0.5 size-4 shrink-0" aria-hidden /> {p.opening_hours}
                  </p>
                )}
                {p.phone_number && (
                  <a href={`tel:${p.phone_number}`} className="flex items-start gap-1.5 hover:text-brand-700">
                    <Phone className="mt-0.5 size-4 shrink-0" aria-hidden /> {formatNgPhone(p.phone_number)}
                  </a>
                )}
              </div>
              <ReportPlace place={p} reasons={reportReasons} loggedIn={loggedIn} loginNext={loginNext} />
            </li>
          ))}
        </ul>
      )}

      <Alert tone="info">
        <span className="flex gap-2">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {NEARBY_NOTICE} Nearby places are <strong>not verified</strong> by PropCheck
            {anyDemo ? "; places marked “Demo data” are fictional examples." : "."}
          </span>
        </span>
      </Alert>
    </div>
  );
}
