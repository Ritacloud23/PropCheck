import type { Metadata } from "next";
import Link from "next/link";

import { LocationFields } from "@/components/location-fields";
import { NearbyPlaces } from "@/components/nearby-places";
import { Alert, Card, Field, PageHeader, Select, buttonClass } from "@/components/ui";
import { stateLabel } from "@/lib/format";
import { getCurrentUser, getReference, serverApi } from "@/lib/server-api";
import type { NearbyResponse, PlaceCategory, ReferenceData } from "@/lib/types";

import { UseMyLocation } from "./use-my-location";

export const metadata: Metadata = {
  title: "What is nearby?",
  description: "Markets, restaurants, churches and clubs near neighbourhoods in Lagos, Port Harcourt, Enugu, Awka and Owerri.",
};

const RADII = ["1", "2", "3", "5", "10"];
const CATEGORIES: PlaceCategory[] = ["MARKET", "RESTAURANT", "CHURCH", "CLUB"];

type Center = { latitude: number; longitude: number; label: string };

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

/** Resolve the search centre: explicit coordinates, else the chosen area, else the chosen city. */
function resolveCenter(ref: ReferenceData, sp: Record<string, string | undefined>): Center | null {
  const lat = Number(sp.lat);
  const lng = Number(sp.lng);
  if (sp.lat && sp.lng && Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
    return { latitude: lat, longitude: lng, label: (sp.label ?? "Selected point").slice(0, 80) };
  }
  const city = (ref.locations[sp.state ?? ""] ?? []).find((c) => c.city === sp.city);
  if (!city) return null;
  const area = city.areas.find((a) => a.area === sp.area);
  if (area) return { latitude: area.latitude, longitude: area.longitude, label: `${area.area}, ${city.city}` };
  return { latitude: city.latitude, longitude: city.longitude, label: `${city.city} centre` };
}

export default async function NearbyPage(props: PageProps<"/nearby">) {
  const raw = await props.searchParams;
  const sp = {
    state: one(raw.state),
    city: one(raw.city),
    area: one(raw.area),
    lat: one(raw.lat),
    lng: one(raw.lng),
    label: one(raw.label),
    radius: one(raw.radius),
    category: one(raw.category),
  };
  const radius = RADII.includes(sp.radius ?? "") ? sp.radius! : "3";
  const initialCategory = CATEGORIES.includes(sp.category as PlaceCategory) ? (sp.category as PlaceCategory) : "ALL";
  const [reference, user] = await Promise.all([getReference(), getCurrentUser()]);
  const center = resolveCenter(reference, sp);
  const result = center
    ? await serverApi<NearbyResponse>(
        `/api/nearby-places?latitude=${center.latitude}&longitude=${center.longitude}&radius_km=${radius}&limit=50`,
        { auth: false },
      ).catch(() => null)
    : null;
  const here = `/nearby?${new URLSearchParams(Object.entries(sp).filter((e): e is [string, string] => !!e[1])).toString()}`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <PageHeader
        title="What is nearby?"
        description="Find markets, restaurants, churches and clubs around a neighbourhood before you inspect a property."
      />
      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <aside className="min-w-0 space-y-4">
          <form action="/nearby" method="get" className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <LocationFields reference={reference} state={sp.state} city={sp.city} area={sp.area} />
            <Field label="Within" htmlFor="n-radius">
              <Select id="n-radius" name="radius" defaultValue={radius}>
                {RADII.map((r) => (
                  <option key={r} value={r}>
                    {r} km
                  </option>
                ))}
              </Select>
            </Field>
            <button type="submit" className={buttonClass("primary", "md", "w-full")}>
              Show nearby places
            </button>
          </form>
          <UseMyLocation radius={radius} />
        </aside>

        <section className="min-w-0" aria-live="polite">
          {!center ? (
            <Card className="p-6">
              <p className="font-semibold text-slate-900">Choose a state and city to start</p>
              <p className="mt-1 text-sm text-slate-600">Or jump straight to a major city:</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {reference.states.map((state) => (
                  <div key={state}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{stateLabel(state)}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(reference.locations[state] ?? [])
                        .filter((c) => c.major)
                        .map((c) => (
                          <Link
                            key={c.city}
                            href={`/nearby?state=${encodeURIComponent(state)}&city=${encodeURIComponent(c.city)}&radius=${radius}`}
                            className="rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-800 hover:bg-brand-50 hover:text-brand-800"
                          >
                            {c.city}
                          </Link>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ) : result === null ? (
            <Alert tone="danger" title="We couldn't load nearby places">Please try again in a moment.</Alert>
          ) : (
            <>
              <p className="mb-3 text-sm text-slate-600">
                {result.count} place{result.count === 1 ? "" : "s"} within {result.radius_km} km of{" "}
                <span className="font-semibold text-slate-900">{center.label}</span>
              </p>
              <NearbyPlaces
                key={`${center.latitude},${center.longitude},${radius}`}
                places={result.items}
                origin={{ latitude: center.latitude, longitude: center.longitude }}
                originLabel={center.label}
                radiusKm={result.radius_km}
                reportReasons={reference.place_report_reasons}
                loggedIn={!!user}
                loginNext={here}
                directionsFromOrigin={false}
                initialCategory={initialCategory}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
