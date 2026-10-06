import type { Metadata } from "next";
import Link from "next/link";

import { AgentCard } from "@/components/agent-card";
import { FilterDrawer } from "@/components/filter-drawer";
import { LocationFields } from "@/components/location-fields";
import { Pagination } from "@/components/pagination";
import { Alert, EmptyState, Field, Input, PageHeader, Select, buttonClass } from "@/components/ui";
import { humanize, propertyTypeLabel } from "@/lib/format";
import { getReference, serverApi } from "@/lib/server-api";
import type { AgentPublic, Page } from "@/lib/types";

export const metadata: Metadata = {
  title: "Find a verified agent",
  description: "Search identity-checked property agents in Lagos, Rivers, Enugu, Anambra and Imo by area, property type and budget.",
};

const KEYS = ["q", "state", "city", "service", "property_type", "budget_max", "verified_only"] as const;

export default async function AgentsPage(props: PageProps<"/agents">) {
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
    serverApi<Page<AgentPublic>>(`/api/agents?${query}`, { auth: false }).catch(() => null),
  ]);
  const activeCount = Object.entries(params).filter(([k, v]) => v && k !== "q").length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Find a verified agent"
        description="Verified Agents have had their identity checked by PropCheck. Their individual listings are verified separately."
      />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="min-w-0">
          <FilterDrawer action="/agents" activeCount={activeCount}>
            <Field label="Name or agency" htmlFor="a-q">
              <Input id="a-q" name="q" defaultValue={params.q} />
            </Field>
            <LocationFields reference={reference} state={params.state} city={params.city} showArea={false} />
            <Field label="Looking to" htmlFor="a-service">
              <Select id="a-service" name="service" defaultValue={params.service ?? ""}>
                <option value="">Any service</option>
                {reference.service_types.map((s) => (
                  <option key={s} value={s}>
                    {s === "RENTAL" ? "Rent" : s === "SALES" ? "Buy" : humanize(s)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Property type" htmlFor="a-type">
              <Select id="a-type" name="property_type" defaultValue={params.property_type ?? ""}>
                <option value="">Any type</option>
                {reference.property_types.map((t) => (
                  <option key={t} value={t}>
                    {propertyTypeLabel(t)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Your max budget (₦/year)" htmlFor="a-budget">
              <Input id="a-budget" name="budget_max" type="number" min={0} step={100000} inputMode="numeric" defaultValue={params.budget_max} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" name="verified_only" value="true" defaultChecked={!!params.verified_only} className="accent-brand-600" />
              Verified agents only
            </label>
          </FilterDrawer>
        </aside>
        <section className="min-w-0" aria-live="polite">
          {result === null ? (
            <Alert tone="danger" title="We couldn't load agents">Please refresh the page.</Alert>
          ) : result.items.length === 0 ? (
            <EmptyState
              title="No agents match these filters"
              action={
                <Link href="/find-an-agent" className={buttonClass("primary", "md")}>
                  Ask PropCheck to find one for you
                </Link>
              }
            >
              Tell us what you need and we&apos;ll match you with a verified agent who covers your area.
            </EmptyState>
          ) : (
            <>
              <p className="mb-4 text-sm text-slate-600">
                {result.total} agent{result.total === 1 ? "" : "s"} found
              </p>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {result.items.map((a) => (
                  <AgentCard key={a.id} agent={a} />
                ))}
              </div>
              <Pagination basePath="/agents" params={params} page={page} pageSize={12} total={result.total} />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
