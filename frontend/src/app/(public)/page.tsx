import { existsSync } from "node:fs";
import path from "node:path";

import { ArrowRight, BadgeCheck, ClipboardCheck, FileSearch, HandCoins, MapPin, UserCheck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { SafetyWarning } from "@/components/disclaimer";
import { PropertyCard } from "@/components/property-card";
import { getReference, serverApi } from "@/lib/server-api";
import type { Page, PropertyCard as PropertyCardT } from "@/lib/types";

import { HeroSearch } from "./hero-search";

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

// Illustrative marketing card with fixed copy. Its button opens real verified Port Harcourt listings,
// each of which has a full report.
function HeroPropertyCard() {
  return (
    <div className="w-full max-w-sm overflow-hidden rounded-3xl bg-white p-3 shadow-2xl shadow-black/25 lg:max-w-none">
      <div className="px-1 pb-3 pt-1">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-highlight/30 px-2.5 py-1 text-xs font-bold text-forest ring-1 ring-highlight">
          <BadgeCheck className="size-3.5" aria-hidden />
          Verified property
        </span>
      </div>
      <Image
        src={HERO_CARD_PHOTO}
        alt="Living room of a modern apartment"
        width={1024}
        height={455}
        sizes="(min-width: 1024px) 320px, 384px"
        className="h-auto w-full rounded-2xl bg-slate-100"
      />
      <div className="px-2 pb-2 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">NEW GRA, ENUGU</p>
        <p className="mt-1.5 text-lg font-bold leading-snug text-deep">Modern 2-bedroom apartment</p>
        <p className="mt-2 text-xl font-extrabold tabular-nums text-deep">
          ₦2,400,000 <span className="text-sm font-medium text-muted">/ year</span>
        </p>
        <ul className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs font-medium text-muted">
          <li className="flex items-center gap-2">
            <BadgeCheck className="size-4 shrink-0 text-forest" aria-hidden /> Verified agent
          </li>
          <li className="flex items-center gap-2">
            <ClipboardCheck className="size-4 shrink-0 text-forest" aria-hidden /> Inspected recently
          </li>
          <li className="flex items-center gap-2">
            {/* Non-breaking spaces keep each distance with its unit on narrow screens. */}
            <MapPin className="size-4 shrink-0 text-forest" aria-hidden /> {"Market 1.1 km · Restaurant 700 m"}
          </li>
        </ul>
        <Link
          href="/properties?verified_only=true&state=Enugu&city=Enugu"
          className="mt-4 flex h-11 w-full items-center justify-center rounded-xl bg-forest text-sm font-bold text-white hover:bg-deep"
        >
          View verification report
        </Link>
      </div>
    </div>
  );
}

// Hero background photo in public/. If the file is missing, the hero falls back to plain dark green.
const HERO_PHOTO = "/hero.png";
const hasHeroPhoto = existsSync(path.join(process.cwd(), "public", HERO_PHOTO));
// Property photo shown inside the floating hero card (1024×455, cropped from hero-2.png to drop its baked-in badge and heart).
const HERO_CARD_PHOTO = "/hero-2-cropped.png";

export default async function HomePage() {
  const [properties, reference] = await Promise.all([featured(), getReference()]);
  return (
    <>
      <section className="px-4 pt-4 sm:px-6 lg:pt-6">
        <div className="mx-auto max-w-7xl">
          <div className="relative overflow-hidden rounded-[2rem] bg-brand-900">
            {hasHeroPhoto && (
              <Image
                src={HERO_PHOTO}
                alt="Bright open-plan living room with a grey sofa, opening onto a kitchen and balcony"
                fill
                preload
                sizes="(min-width: 1280px) 1248px, 100vw"
                className="object-cover"
              />
            )}
            <div aria-hidden className="absolute inset-0 bg-brand-900/80 opacity-70 lg:bg-transparent lg:hero-scrim" />
            <div className="relative grid gap-10 px-5 pb-28 pt-10 sm:px-10 sm:pt-14 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-center lg:gap-12 lg:px-14 lg:pb-32 lg:pt-16 xl:grid-cols-[minmax(0,1fr)_320px]">
              <div className="flex max-w-xl flex-col items-start">
                <p className="inline-flex items-center gap-2 rounded-full bg-forest/75 px-3 py-1.5 text-xs font-semibold text-white ring-1 ring-white/25 backdrop-blur-sm sm:text-sm">
                  <span className="size-2 shrink-0 rounded-full bg-highlight" aria-hidden />
                  Serving Lagos, Enugu, Anambra, Imo and Rivers
                </p>
                <h1 className="mt-6 text-[2.125rem] font-extrabold leading-[1.04] tracking-tight min-[375px]:text-[2.5rem] sm:text-6xl lg:text-[4rem] xl:text-7xl">
                  <span className="block text-white">Find a home</span>
                  <span className="block text-highlight">you can trust.</span>
                </h1>
                <p className="mt-4 max-w-lg text-base leading-relaxed text-white/85 sm:text-lg">
                  Connect with trusted agents, explore verified properties and discover what is nearby before you pay rent.
                </p>
                <div className="mt-8 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
                  <Link
                    href="/properties"
                    className="inline-flex h-12 items-center justify-center rounded-full bg-highlight px-7 font-bold text-forest transition-colors hover:bg-lime-200"
                  >
                    Browse properties
                  </Link>
                  <Link
                    href="/agents?verified_only=true"
                    className="inline-flex h-12 items-center justify-center rounded-full bg-forest/70 px-7 font-bold text-white ring-1 ring-white/50 backdrop-blur-sm transition-colors hover:bg-forest"
                  >
                    Find a verified agent
                  </Link>
                </div>
              </div>
              <div className="flex justify-start lg:justify-end">
                <HeroPropertyCard />
              </div>
            </div>
          </div>
          <div className="relative z-10 -mt-20 sm:mx-4 lg:mx-8">
            <HeroSearch reference={reference} />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <FeatureGrid />
      </section>

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
