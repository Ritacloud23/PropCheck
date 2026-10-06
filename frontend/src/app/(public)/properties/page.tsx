import type { Metadata } from "next";
import Link from "next/link";

import { FilterDrawer } from "@/components/filter-drawer";
import { LocationFields } from "@/components/location-fields";
import { Pagination } from "@/components/pagination";
import { PropertyCard } from "@/components/property-card";
import { Alert, EmptyState, Field, Input, PageHeader, Select, buttonClass } from "@/components/ui";
import { propertyTypeLabel } from "@/lib/format";
import { getReference, serverApi } from "@/lib/server-api";
import type { Page, PropertyCard as PropertyCardT } from "@/lib/types";

export const metadata: Metadata = {
  title: "Rental properties in Lagos, Port Harcourt, Enugu, Awka & Owerri",
  description: "Search rental listings with transparent fees and independent verification reports.",
};

const KEYS = [
  "q", "state", "city", "area", "property_type", "bedrooms", "rent_min", "rent_max",
  "verification", "verified_only", "available_only", "sort",
] as const;

export default async function PropertiesPage(props: PageProps<"/properties">) {
  const raw = await props.searchParams;
  const params: Record<string, string | undefined> = {};
  for (const k of KEYS) {
    const v = raw[k];
    params[k] = Array.isArray(v) ? v[0] : v;
  }
  const page = Math.max(1, Number(raw.page) || 1);
  const query = new URLSearchParams({ page: String(page), page_size: "12" });
  for (const [k, v] of Object.entries(params)) if (v) query.set(k, v);

  const [reference, result] = await Promise.all([
    getReference(),
    serverApi<Page<PropertyCardT>>(`/api/properties?${query}`, { auth: false }).catch(() => null),
  ]);
  const activeCount = Object.entries(params).filter(([k, v]) => v && k !== "sort" && k !== "q").length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Find a rental"
        description="Every card shows whether the listing has been verified. Open a listing to read its full report."
      />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="min-w-0">
          <FilterDrawer action="/properties" activeCount={activeCount}>
            <Field label="Search" htmlFor="f-q">
              <Input id="f-q" name="q" defaultValue={params.q} placeholder="Title, area or landmark" />
            </Field>
            <LocationFields reference={reference} state={params.state} city={params.city} area={params.area} />
            <Field label="Property type" htmlFor="f-type">
              <Select id="f-type" name="property_type" defaultValue={params.property_type ?? ""}>
                <option value="">Any type</option>
                {reference.property_types.map((t) => (
                  <option key={t} value={t}>
                    {propertyTypeLabel(t)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Bedrooms (minimum)" htmlFor="f-beds">
              <Select id="f-beds" name="bedrooms" defaultValue={params.bedrooms ?? ""}>
                <option value="">Any</option>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}+
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Min rent (₦)" htmlFor="f-min">
                <Input id="f-min" name="rent_min" type="number" min={0} step={50000} inputMode="numeric" defaultValue={params.rent_min} />
              </Field>
              <Field label="Max rent (₦)" htmlFor="f-max">
                <Input id="f-max" name="rent_max" type="number" min={0} step={50000} inputMode="numeric" defaultValue={params.rent_max} />
              </Field>
            </div>
            <Field label="Verification" htmlFor="f-ver">
              <Select id="f-ver" name="verification" defaultValue={params.verified_only ? "verified" : (params.verification ?? "any")}>
                <option value="any">Any status</option>
                <option value="verified">Verified only</option>
                <option value="pending">Verification in progress</option>
                <option value="not_verified">Not verified</option>
              </Select>
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" name="available_only" value="true" defaultChecked={!!params.available_only} className="accent-brand-600" />
              Available now
            </label>
            <Field label="Sort by" htmlFor="f-sort">
              <Select id="f-sort" name="sort" defaultValue={params.sort ?? "newest"}>
                <option value="newest">Newest first</option>
                <option value="rent_asc">Rent: low to high</option>
                <option value="rent_desc">Rent: high to low</option>
              </Select>
            </Field>
          </FilterDrawer>
        </aside>

        <section className="min-w-0" aria-live="polite">
          {result === null ? (
            <Alert tone="danger" title="We couldn't load listings">
              Please refresh the page. If this keeps happening, the service may be down.
            </Alert>
          ) : result.items.length === 0 ? (
            <EmptyState
              title="No properties match these filters"
              action={
                <Link href="/properties" className={buttonClass("secondary", "md")}>
                  Clear filters
                </Link>
              }
            >
              Try a nearby area, a wider budget, or include listings that are still being verified.
            </EmptyState>
          ) : (
            <>
              <p className="mb-4 text-sm text-slate-600">
                {result.total} propert{result.total === 1 ? "y" : "ies"} found
              </p>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {result.items.map((p) => (
                  <PropertyCard key={p.id} property={p} />
                ))}
              </div>
              <Pagination basePath="/properties" params={params} page={page} pageSize={12} total={result.total} />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
