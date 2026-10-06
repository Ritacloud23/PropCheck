import { Bath, BedDouble, MapPin } from "lucide-react";
import Link from "next/link";

import { formatNaira, placeLabel, propertyTypeLabel } from "@/lib/format";
import { localMedia } from "@/lib/media";
import type { PropertyCard as PropertyCardT } from "@/lib/types";

import { VerifiedAgentBadge, VerifiedPropertyBadge } from "./badges";
import { Pill } from "./ui";

const AVAILABILITY_LABEL: Record<string, string> = { LET: "Let", RESERVED: "Reserved", UNAVAILABLE: "Unavailable" };

export function PropertyCard({ property: p, href }: { property: PropertyCardT; href?: string }) {
  const img = localMedia(p.cover_photo_url);
  return (
    <Link
      href={href ?? `/properties/${p.public_slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-slate-100">
        {img ? (
          // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
          <img src={img} alt="" className="absolute inset-0 size-full object-cover" loading="lazy" />
        ) : (
          <div className="flex size-full items-center justify-center text-sm text-slate-400">No photo yet</div>
        )}
        <div className="absolute left-3 top-3">
          <VerifiedPropertyBadge status={p.verification.status} expiresAt={p.verification.expires_at} />
        </div>
        {p.availability_status !== "AVAILABLE" && (
          <div className="absolute right-3 top-3">
            <Pill tone="neutral" className="bg-white">
              {AVAILABILITY_LABEL[p.availability_status]}
            </Pill>
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <p className="text-lg font-bold tabular-nums text-slate-900">
          {formatNaira(p.rent_amount)}
          <span className="text-sm font-normal text-slate-500"> /year</span>
        </p>
        <h3 className="line-clamp-2 font-semibold text-slate-900 group-hover:text-brand-700">{p.title}</h3>
        <p className="flex items-center gap-1 text-sm text-slate-600">
          <MapPin className="size-3.5 shrink-0" aria-hidden />
          {placeLabel(p)}
        </p>
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <span>{propertyTypeLabel(p.property_type)}</span>
          {p.bedrooms > 0 && (
            <span className="flex items-center gap-1">
              <BedDouble className="size-4" aria-label="Bedrooms" /> {p.bedrooms}
            </span>
          )}
          {p.bathrooms > 0 && (
            <span className="flex items-center gap-1">
              <Bath className="size-4" aria-label="Bathrooms" /> {p.bathrooms}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">
          Total move-in: <span className="font-semibold text-slate-700">{formatNaira(p.total_move_in_cost)}</span>
        </p>
        {p.agent && (
          <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
            <span className="truncate">Listed by {p.agent.agency_name ?? p.agent.name}</span>
            <VerifiedAgentBadge status={p.agent.verification_status} expiresAt={p.agent.verification_expiry_date} />
          </div>
        )}
      </div>
    </Link>
  );
}

export function PropertyCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="aspect-[16/10] animate-pulse bg-slate-200" />
      <div className="space-y-3 p-4">
        <div className="h-5 w-1/3 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-3/4 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
      </div>
    </div>
  );
}
