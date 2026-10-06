import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  HandCoins,
  MapPin,
  Search,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import Link from "next/link";

import { VerifiedPropertyBadge } from "@/components/badges";
import { SafetyWarning } from "@/components/disclaimer";
import { PropertyCard } from "@/components/property-card";
import { buttonClass, Select } from "@/components/ui";
import { formatNaira, placeLabel } from "@/lib/format";
import { localMedia } from "@/lib/media";
import { serverApi } from "@/lib/server-api";
import type { Page, PropertyCard as PropertyCardT } from "@/lib/types";

async function featured(): Promise<PropertyCardT[]> {
  try {
    const page = await serverApi<Page<PropertyCardT>>("/api/properties?verified_only=true&page_size=6", { auth: false });
    return page.items;
  } catch {
    return [];
  }
}

const FEATURES = [
  { icon: UserCheck, title: "Verified Agent", body: "Identity and business documents reviewed by a person, not a bot." },
  { icon: ClipboardCheck, title: "Verified Property", body: "Authority to let, location, photos and fees checked — with an expiry date." },
  { icon: FileSearch, title: "Transparent report", body: "See every check, what passed, and what PropCheck did not check." },
  { icon: HandCoins, title: "No hidden fees", body: "Rent, agency, legal and caution fees shown with the total move-in cost." },
];

function FeatureGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {FEATURES.map((f) => (
        <div key={f.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <f.icon className="size-6 text-brand-600" aria-hidden />
          <p className="mt-3 font-semibold text-slate-900">{f.title}</p>
          <p className="mt-1 text-sm text-slate-600">{f.body}</p>
        </div>
      ))}
    </div>
  );
}

// Every currently verified property passed these mandatory checks, so this list is always true.
const HERO_CHECKS = ["Authority to let seen", "Location inspected", "Fees confirmed"];

function HeroListing({ property: p }: { property: PropertyCardT }) {
  const img = localMedia(p.cover_photo_url);
  return (
    <div className="relative mx-auto w-full max-w-md lg:max-w-none">
      <Link
        href={`/properties/${p.public_slug}`}
        className="group block overflow-hidden rounded-3xl bg-white shadow-2xl shadow-brand-900/10 ring-1 ring-slate-200 transition hover:-translate-y-1 lg:rotate-1 lg:hover:rotate-0"
      >
        <div className="relative aspect-[4/3] overflow-hidden bg-slate-100">
          {img && (
            // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
            <img src={img} alt={p.title} className="absolute inset-0 size-full object-cover transition group-hover:scale-105" />
          )}
          <div className="absolute left-4 top-4">
            <VerifiedPropertyBadge status={p.verification.status} expiresAt={p.verification.expires_at} />
          </div>
        </div>
        <div className="space-y-3 p-5">
          <p className="text-2xl font-extrabold tabular-nums text-slate-900">
            {formatNaira(p.rent_amount)}
            <span className="text-sm font-normal text-slate-500"> /year</span>
          </p>
          <p className="font-semibold text-slate-900">{p.title}</p>
          <p className="flex items-center gap-1 text-sm text-slate-600">
            <MapPin className="size-4 shrink-0" aria-hidden /> {placeLabel(p)}
          </p>
          <ul className="grid gap-1.5 border-t border-slate-100 pt-3 text-sm text-slate-700">
            {HERO_CHECKS.map((c) => (
              <li key={c} className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-green-600" aria-hidden /> {c}
              </li>
            ))}
          </ul>
        </div>
      </Link>
      {p.agent?.is_verified && (
        <div className="absolute -left-6 top-1/3 hidden items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm shadow-lg ring-1 ring-slate-200 sm:flex">
          <BadgeCheck className="size-5 text-brand-600" aria-hidden />
          <span>
            <span className="block text-xs text-slate-500">Listed by</span>
            <span className="font-semibold text-slate-900">Verified Agent</span>
          </span>
        </div>
      )}
      {p.verification.reference && (
        <div className="absolute -right-3 -top-4 hidden rounded-xl bg-slate-900 px-3 py-2 text-xs text-white shadow-lg sm:block">
          Report <span className="font-mono">{p.verification.reference}</span>
        </div>
      )}
    </div>
  );
}

export default async function HomePage() {
  const properties = await featured();
  // Showcase a real verified listing: prefer a family-size home with a photo.
  const hero =
    properties.find((p) => p.cover_photo_url && p.bedrooms >= 2 && p.agent?.is_verified) ??
    properties.find((p) => p.cover_photo_url) ??
    null;
  return (
    <>
      <section className="relative overflow-hidden border-b border-slate-200 bg-gradient-to-br from-brand-50 via-white to-emerald-50">
        <div aria-hidden className="pointer-events-none absolute -right-32 -top-32 size-96 rounded-full bg-brand-100/60 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-40 left-1/3 size-96 rounded-full bg-emerald-100/50 blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-medium text-brand-800 shadow-sm ring-1 ring-brand-100">
              <ShieldCheck className="size-4" aria-hidden /> Now in Lagos, Port Harcourt, Enugu, Awka & Owerri
            </p>
            <h1 className="mt-5 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
              Verify the property and agent <span className="text-brand-600">before you pay rent.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600">
              PropCheck reviewers check agent identity, authority to let, location, photos and the full fee breakdown —
              and show you exactly what was and wasn&apos;t checked.
            </p>

            <form
              action="/properties"
              className="mt-8 grid gap-2 rounded-2xl bg-white p-2 shadow-lg shadow-brand-900/5 ring-1 ring-slate-200 sm:grid-cols-[1fr_1.3fr_auto]"
            >
              <label className="sr-only" htmlFor="hero-state">State</label>
              <Select id="hero-state" name="state" defaultValue="Lagos">
                <option value="Lagos">Lagos</option>
                <option value="Rivers">Rivers (Port Harcourt)</option>
                <option value="Enugu">Enugu</option>
                <option value="Anambra">Anambra</option>
                <option value="Imo">Imo</option>
                <option value="">All states</option>
              </Select>
              <label className="sr-only" htmlFor="hero-q">Area or keyword</label>
              <input
                id="hero-q"
                name="q"
                placeholder="Area, e.g. Lekki, GRA Phase 2, Independence Layout"
                className="h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-base sm:text-sm"
              />
              <button className={buttonClass("primary", "md")}>
                <Search className="size-4" aria-hidden /> Search
              </button>
              <label className="col-span-full flex items-center gap-2 px-2 pb-1 text-sm text-slate-600">
                <input type="checkbox" name="verified_only" value="true" defaultChecked className="accent-brand-600" />
                Only show verified properties
              </label>
            </form>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/agents?verified_only=true" className={buttonClass("secondary", "lg")}>
                <BadgeCheck className="size-5" aria-hidden /> Find a verified agent
              </Link>
              <Link href="/find-an-agent" className={buttonClass("ghost", "lg")}>
                Help me find a house <ArrowRight className="size-4" aria-hidden />
              </Link>
            </div>
          </div>

          {hero ? <HeroListing property={hero} /> : <FeatureGrid />}
        </div>
      </section>

      {hero && (
        <section className="border-b border-slate-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
            <FeatureGrid />
          </div>
        </section>
      )}

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Recently verified homes</h2>
            <p className="text-slate-600">Each listing links to its full verification report.</p>
          </div>
          <Link href="/properties?verified_only=true" className="hidden text-sm font-semibold text-brand-700 hover:underline sm:block">
            See all verified →
          </Link>
        </div>
        {properties.length ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {properties.map((p) => (
              <PropertyCard key={p.id} property={p} />
            ))}
          </div>
        ) : (
          <p className="rounded-xl bg-white p-8 text-center text-slate-500 ring-1 ring-slate-200">
            No verified listings yet. Check back soon.
          </p>
        )}
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
          <h2 className="text-2xl font-bold text-slate-900">Two separate checks — on purpose</h2>
          <p className="mt-1 max-w-2xl text-slate-600">
            A verified agent can still list a property that hasn&apos;t been checked. Look for both badges.
          </p>
          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-6 ring-1 ring-slate-200">
              <p className="font-semibold text-slate-900">1 · Agent verification</p>
              <p className="mt-2 text-sm text-slate-600">
                We confirm who the agent is (government ID, business registration where available) and how to reach them.
                Agents can be suspended after complaints.
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-6 ring-1 ring-slate-200">
              <p className="font-semibold text-slate-900">2 · Property verification</p>
              <p className="mt-2 text-sm text-slate-600">
                A reviewer checks the agent&apos;s authority to let this specific property, inspects the location, compares
                photos and confirms the fees. Every report has a reference number and an expiry date.
              </p>
            </div>
          </div>
          <SafetyWarning className="mt-6" />
          <Link href="/how-it-works" className="mt-6 inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
            How verification works <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </section>
    </>
  );
}
