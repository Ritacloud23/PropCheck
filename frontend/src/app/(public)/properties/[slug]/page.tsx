import { Bath, BedDouble, Flag, MapPin, Pencil, Sofa } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentAvatar } from "@/components/agent-card";
import { VerifiedAgentBadge, VerifiedPropertyBadge } from "@/components/badges";
import { SafetyWarning } from "@/components/disclaimer";
import { FeeBreakdown } from "@/components/fee-breakdown";
import { BookInspection, ReserveProperty, ShareButtons } from "@/components/property-actions";
import { NearbyPlaces } from "@/components/nearby-places";
import { PropertyMap } from "@/components/property-map";
import { VerificationReport } from "@/components/verification-report";
import { CallButton, WhatsAppButton } from "@/components/whatsapp-button";
import { Card, CardHeader, Pill, buttonClass } from "@/components/ui";
import { formatNaira, placeLabel, propertyTypeLabel, stateLabel } from "@/lib/format";
import { localMedia } from "@/lib/media";
import { getCurrentUser, getReference, serverApi, serverApiOrNull } from "@/lib/server-api";
import type { NearbyResponse, PropertyDetail, Slot, VerificationReport as Report } from "@/lib/types";
import { enquiryMessage } from "@/lib/whatsapp";

const NEARBY_RADIUS_KM = 3;

async function load(slug: string) {
  return serverApiOrNull<PropertyDetail>(`/api/properties/${encodeURIComponent(slug)}`);
}

export async function generateMetadata(props: PageProps<"/properties/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const p = await load(slug);
  if (!p) return { title: "Property not found" };
  const verified = p.verification.is_currently_verified ? "Verified · " : "";
  return {
    title: `${p.title} — ${p.city}`,
    description: `${verified}${formatNaira(p.rent_amount)}/year · ${propertyTypeLabel(p.property_type)} in ${p.city}, ${stateLabel(p.state)}. Total move-in ${formatNaira(p.total_move_in_cost)}.`,
    openGraph: { images: p.cover_photo_url ? [p.cover_photo_url] : undefined },
  };
}

export default async function PropertyPage(props: PageProps<"/properties/[slug]">) {
  const { slug } = await props.params;
  const [p, user] = await Promise.all([load(slug), getCurrentUser()]);
  if (!p) notFound();
  const hasLocation = p.latitude !== null && p.longitude !== null;
  const [report, slots, terms, nearby, reference] = await Promise.all([
    serverApi<Report>(`/api/properties/${p.id}/verification-report`, { auth: false }),
    serverApi<Slot[]>(`/api/properties/${p.id}/slots`, { auth: false }).catch(() => []),
    serverApi<{ terms: string[]; amount: number | null }>(`/api/reservations/terms?property_id=${p.id}`, { auth: false }),
    hasLocation
      ? serverApi<NearbyResponse>(
          `/api/nearby-places?latitude=${p.latitude}&longitude=${p.longitude}&radius_km=${NEARBY_RADIUS_KM}&limit=50`,
          { auth: false },
        ).catch(() => null)
      : Promise.resolve(null),
    getReference(),
  ]);
  const path = `/properties/${p.public_slug}`;
  const agent = p.agent_profile;
  const photos = p.media.map((m) => ({ ...m, url: localMedia(m.url)! }));

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <nav className="mb-4 text-sm text-slate-500" aria-label="Breadcrumb">
        <Link href="/properties" className="hover:text-brand-700">Properties</Link> /{" "}
        <Link href={`/properties?state=${p.state}&city=${encodeURIComponent(p.city)}`} className="hover:text-brand-700">
          {p.city}
        </Link>
      </nav>

      {p.can_manage && (user?.role === "AGENT" || user?.role === "LANDLORD") && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white">
          <span>You manage this listing.</span>
          <Link href={`/dashboard/agent/properties/${p.id}`} className={buttonClass("secondary", "sm")}>
            <Pencil className="size-4" aria-hidden /> Manage listing & verification
          </Link>
        </div>
      )}

      <div className="grid gap-2 overflow-hidden rounded-2xl sm:grid-cols-3 sm:grid-rows-2">
        {photos.length ? (
          photos.slice(0, 3).map((m, i) => (
            // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
            <img
              key={m.id}
              src={m.url}
              alt={m.caption ?? p.title}
              className={`size-full bg-slate-100 object-cover ${i === 0 ? "aspect-[16/10] sm:col-span-2 sm:row-span-2" : "hidden aspect-[16/10] sm:block"}`}
            />
          ))
        ) : (
          <div className="flex aspect-[16/7] items-center justify-center bg-slate-100 text-slate-400 sm:col-span-3 sm:row-span-2">
            No photos uploaded yet
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-8">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <VerifiedPropertyBadge status={p.verification.status} expiresAt={p.verification.expires_at} />
              {p.availability_status !== "AVAILABLE" && <Pill>{p.availability_status === "LET" ? "Let" : p.availability_status === "RESERVED" ? "Reserved" : "Unavailable"}</Pill>}
            </div>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{p.title}</h1>
            <p className="mt-2 flex items-center gap-1.5 text-slate-600">
              <MapPin className="size-4 shrink-0" aria-hidden />
              {p.landmark ? `${p.landmark}, ` : ""}
              {placeLabel(p)}
              {p.local_government_area ? ` · ${p.local_government_area} LGA` : ""}
            </p>
            <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-700">
              <span className="rounded-lg bg-white px-3 py-1.5 ring-1 ring-slate-200">{propertyTypeLabel(p.property_type)}</span>
              {p.bedrooms > 0 && (
                <span className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 ring-1 ring-slate-200">
                  <BedDouble className="size-4" aria-hidden /> {p.bedrooms} bedroom{p.bedrooms > 1 ? "s" : ""}
                </span>
              )}
              {p.bathrooms > 0 && (
                <span className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 ring-1 ring-slate-200">
                  <Bath className="size-4" aria-hidden /> {p.bathrooms} bathroom{p.bathrooms > 1 ? "s" : ""}
                </span>
              )}
              <span className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 ring-1 ring-slate-200">
                <Sofa className="size-4" aria-hidden /> {p.furnished ? "Furnished" : "Unfurnished"}
              </span>
            </div>
            {p.description && <p className="mt-5 whitespace-pre-line text-slate-700">{p.description}</p>}
          </div>

          <Card>
            <CardHeader title="Verification report" description="Exactly what PropCheck checked — and what it didn't." />
            <div className="p-5">
              <VerificationReport report={report} />
            </div>
          </Card>

          {hasLocation && nearby ? (
            <Card id="nearby">
              <CardHeader
                title="What is nearby?"
                description={`Markets, restaurants, churches and clubs within ${NEARBY_RADIUS_KM} km. The green circle is the property's approximate area.`}
              />
              <div className="p-5">
                <NearbyPlaces
                  places={nearby.items}
                  origin={{ latitude: p.latitude!, longitude: p.longitude! }}
                  originLabel="This property"
                  radiusKm={NEARBY_RADIUS_KM}
                  reportReasons={reference.place_report_reasons}
                  loggedIn={!!user}
                  loginNext={`${path}#nearby`}
                />
                <Link
                  href={`/nearby?lat=${p.latitude}&lng=${p.longitude}&label=${encodeURIComponent(p.title)}`}
                  className="mt-3 inline-block text-sm font-semibold text-brand-700 hover:underline"
                >
                  Search a wider area →
                </Link>
              </div>
            </Card>
          ) : (
            <Card>
              <CardHeader title="Location" description="Approximate area. The exact address is confirmed at inspection." />
              <div className="p-5">
                <PropertyMap lat={p.latitude} lng={p.longitude} label={p.title} />
              </div>
            </Card>
          )}
        </div>

        <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
          <Card className="p-5">
            <p className="text-3xl font-extrabold tabular-nums text-slate-900">
              {formatNaira(p.rent_amount)}
              <span className="text-base font-normal text-slate-500"> /year</span>
            </p>
            <div className="mt-4">
              <FeeBreakdown fees={p.fees} />
            </div>
          </Card>

          <SafetyWarning />

          {agent && (
            <Card className="p-5">
              <p className="mb-3 text-sm font-semibold text-slate-500">Listed by</p>
              <div className="flex items-start gap-3">
                <AgentAvatar name={agent.name} photo={agent.profile_photo_url} />
                <div className="min-w-0">
                  <Link href={`/agents/${agent.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
                    {agent.name}
                  </Link>
                  {agent.agency_name && <p className="text-sm text-slate-600">{agent.agency_name}</p>}
                  <div className="mt-1.5">
                    <VerifiedAgentBadge status={agent.verification_status} expiresAt={agent.verification_expiry_date} />
                  </div>
                </div>
              </div>
              {agent.is_verified && !p.verification.is_currently_verified && (
                <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  The agent is verified, but this specific property has not been verified.
                </p>
              )}
              <div className="mt-4 grid gap-2">
                {agent.contact_public ? (
                  <>
                    <WhatsAppButton number={agent.whatsapp_number} message={enquiryMessage(p.title, p.share_url)} className="w-full" />
                    <CallButton number={agent.phone_number} className="w-full" />
                  </>
                ) : (
                  <p className="text-sm text-slate-600">
                    This agent shares contact details only after you book an inspection or{" "}
                    <Link href={`/find-an-agent?agent=${agent.id}`} className="font-semibold text-brand-700 hover:underline">
                      request help
                    </Link>
                    .
                  </p>
                )}
              </div>
            </Card>
          )}

          <Card className="p-5">
            <h2 className="mb-3 font-semibold text-slate-900">Book an inspection</h2>
            <BookInspection slots={slots} role={user?.role ?? null} path={path} />
          </Card>

          {p.verification.is_currently_verified && p.availability_status === "AVAILABLE" && (
            <Card className="p-5">
              <h2 className="font-semibold text-slate-900">Reserve (test mode)</h2>
              <p className="mb-3 mt-1 text-xs text-slate-500">
                Demonstrates a hold-until-keys flow. No real money moves; Paystack runs in test mode.
              </p>
              <ReserveProperty propertyId={p.id} amount={terms.amount ?? 0} terms={terms.terms} role={user?.role ?? null} path={path} />
            </Card>
          )}

          <div className="space-y-3">
            <ShareButtons url={p.share_url} title={p.title} />
            <Link href={`/report-problem?property=${p.id}`} className="inline-flex items-center gap-1.5 text-sm text-red-700 hover:underline">
              <Flag className="size-4" aria-hidden /> Report a problem with this listing
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
