import { Briefcase, MapPin, Star } from "lucide-react";
import Link from "next/link";

import { stateLabel } from "@/lib/format";
import { localMedia } from "@/lib/media";
import type { AgentPublic } from "@/lib/types";

import { VerifiedAgentBadge } from "./badges";
import { buttonClass } from "./ui";
import { WhatsAppButton } from "./whatsapp-button";

export function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
}

export function AgentAvatar({ name, photo, size = "md" }: { name: string; photo: string | null; size?: "md" | "lg" }) {
  const cls = size === "lg" ? "size-20 text-2xl" : "size-12 text-base";
  const src = localMedia(photo);
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
    return <img src={src} alt="" className={`${cls} shrink-0 rounded-full object-cover`} />;
  }
  return (
    <div className={`${cls} flex shrink-0 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-800`}>
      {initials(name)}
    </div>
  );
}

export function AgentCard({ agent }: { agent: AgentPublic }) {
  const extraCities = agent.cities_covered.length - 4;
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <AgentAvatar name={agent.name} photo={agent.profile_photo_url} />
        <div className="min-w-0 flex-1">
          <Link href={`/agents/${agent.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
            {agent.name}
          </Link>
          {agent.agency_name && <p className="truncate text-sm text-slate-600">{agent.agency_name}</p>}
          <div className="mt-1.5">
            <VerifiedAgentBadge status={agent.verification_status} expiresAt={agent.verification_expiry_date} />
          </div>
        </div>
      </div>
      <div className="space-y-1.5 text-sm text-slate-600">
        <p className="flex items-start gap-1.5">
          <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {agent.cities_covered.slice(0, 4).join(", ") || "—"}
            {extraCities > 0 && ` +${extraCities}`} · {agent.states_covered.map(stateLabel).join(", ")}
          </span>
        </p>
        <p className="flex items-center gap-1.5">
          <Briefcase className="size-4 shrink-0" aria-hidden /> {agent.years_experience} yrs experience ·{" "}
          {agent.active_listings} listing{agent.active_listings === 1 ? "" : "s"}
        </p>
        {agent.average_rating !== null && (
          <p className="flex items-center gap-1.5">
            <Star className="size-4 shrink-0 fill-amber-400 text-amber-400" aria-hidden />
            {agent.average_rating.toFixed(1)} ({agent.total_reviews} reviews)
          </p>
        )}
      </div>
      <div className="mt-auto flex flex-wrap gap-2">
        <Link href={`/agents/${agent.id}`} className={buttonClass("secondary", "sm", "flex-1")}>
          View profile
        </Link>
        {agent.contact_public ? (
          <WhatsAppButton
            number={agent.whatsapp_number}
            message={`Hello ${agent.name.split(" ")[0]}, I found you on PropCheck Nigeria and I'm looking for a property.`}
            className="h-9 flex-1 text-sm"
          />
        ) : (
          <Link href={`/find-an-agent?agent=${agent.id}`} className={buttonClass("primary", "sm", "flex-1")}>
            Request help
          </Link>
        )}
      </div>
    </div>
  );
}
