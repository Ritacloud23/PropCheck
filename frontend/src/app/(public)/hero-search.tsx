"use client";

import { ArrowRight, Building2, MapPin, Wallet } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { stateLabel } from "@/lib/format";
import type { ReferenceData } from "@/lib/types";
import { cn } from "@/lib/utils";

// Each tab submits to a page that already reads these query params.
// PropCheck lists rentals only, so "Buy" finds agents who handle sales.
const TABS = [
  { id: "rent", label: "Rent", action: "/properties", submit: "Search homes" },
  { id: "buy", label: "Buy", action: "/agents", submit: "Find sales agents" },
  { id: "agents", label: "Find an agent", action: "/agents", submit: "Find agents" },
] as const;

// value = "min-max" in naira per year; either side may be empty.
const BUDGETS = [
  { value: "", label: "Any budget" },
  { value: "-1000000", label: "Under ₦1m" },
  { value: "1000000-5000000", label: "₦1m – ₦5m" },
  { value: "5000000-10000000", label: "₦5m – ₦10m" },
  { value: "10000000-", label: "Above ₦10m" },
];
const DEFAULT_BUDGET = "1000000-5000000";

function SearchField({ id, label, icon, children }: { id: string; label: string; icon: ReactNode; children: ReactNode }) {
  return (
    <div className="flex h-14 min-w-0 items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 focus-within:border-forest">
      <span className="shrink-0 text-muted">{icon}</span>
      <div className="min-w-0 flex-1">
        <label htmlFor={id} className="block text-xs font-medium leading-tight text-muted">
          {label}
        </label>
        {children}
      </div>
    </div>
  );
}

const valueClass =
  "w-full min-w-0 truncate bg-transparent py-0.5 text-sm font-semibold text-deep outline-none disabled:cursor-not-allowed disabled:text-slate-400";

export function HeroSearch({ reference }: { reference: Pick<ReferenceData, "states" | "locations"> }) {
  const router = useRouter();
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [budget, setBudget] = useState(DEFAULT_BUDGET);

  function submit(e: FormEvent<HTMLFormElement>) {
    // Without JavaScript the form still submits as a plain GET; this just drops empty params.
    e.preventDefault();
    const params = new URLSearchParams();
    if (state) params.set("state", state);
    if (city.trim()) params.set("city", city.trim());
    if (tab.id === "rent" && budget) {
      const [min, max] = budget.split("-");
      if (min) params.set("rent_min", min);
      if (max) params.set("rent_max", max);
    }
    if (tab.id === "buy") params.set("service", "SALES");
    const qs = params.toString();
    router.push(qs ? `${tab.action}?${qs}` : tab.action);
  }

  return (
    <div className="rounded-3xl bg-white p-3 shadow-xl shadow-forest/10 ring-1 ring-slate-200 sm:p-4">
      <div role="tablist" aria-label="What are you looking for?" className="flex gap-1 overflow-x-auto border-b border-slate-100 pb-3">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab.id === t.id}
            aria-controls="hero-search-panel"
            onClick={() => setTab(t)}
            className={cn(
              "shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition-colors",
              tab.id === t.id ? "bg-forest text-white" : "text-muted hover:bg-cream hover:text-deep",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <form
        id="hero-search-panel"
        role="tabpanel"
        action={tab.action}
        onSubmit={submit}
        className={cn(
          "mt-3 grid gap-2 sm:grid-cols-2 md:gap-3",
          tab.id === "rent" ? "lg:grid-cols-[1fr_1fr_1fr_auto]" : "lg:grid-cols-[1fr_1fr_auto] [&>button]:sm:col-span-2 [&>button]:lg:col-span-1",
        )}
      >
        <SearchField id="hero-state" label="State" icon={<MapPin className="size-5" aria-hidden />}>
          <select
            id="hero-state"
            name="state"
            value={state}
            onChange={(e) => setState(e.target.value)}
            className={cn(valueClass, "cursor-pointer appearance-none")}
          >
            <option value="">Choose a state</option>
            {reference.states.map((s) => (
              <option key={s} value={s}>
                {stateLabel(s)}
              </option>
            ))}
          </select>
        </SearchField>
        <SearchField id="hero-city" label="City or area" icon={<Building2 className="size-5" aria-hidden />}>
          <input
            id="hero-city"
            name="city"
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="e.g. Ikeja"
            autoComplete="off"
            maxLength={80}
            className={cn(valueClass, "placeholder:text-deep/60")}
          />
        </SearchField>
        {tab.id === "rent" && (
          <SearchField id="hero-budget" label="Budget" icon={<Wallet className="size-5" aria-hidden />}>
            <select
              id="hero-budget"
              name="budget"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className={cn(valueClass, "cursor-pointer appearance-none")}
            >
              {BUDGETS.map((b) => (
                <option key={b.value} value={b.value}>
                  {b.label}
                </option>
              ))}
            </select>
          </SearchField>
        )}
        <button
          type="submit"
          className="inline-flex h-14 items-center justify-center gap-2 rounded-xl bg-forest px-6 text-sm font-bold text-white transition-colors hover:bg-deep"
        >
          {tab.submit} <ArrowRight className="size-4" aria-hidden />
        </button>
      </form>
      <div className="mt-3 flex flex-col gap-1 px-1 text-xs sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <p className="font-medium text-deep">Currently serving Lagos, Enugu, Anambra, Imo and Rivers.</p>
        <p className="text-muted">Do not send money before confirming the property, agent authority and payment terms.</p>
      </div>
    </div>
  );
}
