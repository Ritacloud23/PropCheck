import { Briefcase, Clock, Flag, MapPin, ShieldAlert, Star, Users } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AgentAvatar } from "@/components/agent-card";
import { VerifiedAgentBadge } from "@/components/badges";
import { SafetyWarning } from "@/components/disclaimer";
import { PropertyCard } from "@/components/property-card";
import { Alert, Card, DefinitionRow, EmptyState, buttonClass } from "@/components/ui";
import { CallButton, WhatsAppButton } from "@/components/whatsapp-button";
import { formatDate, formatNaira, humanize, propertyTypeLabel, stateLabel } from "@/lib/format";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AgentPublic, PropertyCard as PropertyCardT } from "@/lib/types";

export async function generateMetadata(props: PageProps<"/agents/[id]">): Promise<Metadata> {
  const { id } = await props.params;
  const a = await serverApiOrNull<AgentPublic>(`/api/agents/${Number(id) || 0}`);
  return a ? { title: `${a.name}${a.agency_name ? ` · ${a.agency_name}` : ""}` } : { title: "Agent not found" };
}

export default async function AgentPage(props: PageProps<"/agents/[id]">) {
  const { id } = await props.params;
  const agentId = Number(id);
  if (!Number.isInteger(agentId)) notFound();
  const agent = await serverApiOrNull<AgentPublic>(`/api/agents/${agentId}`);
  if (!agent) notFound();
  const listings = await serverApi<PropertyCardT[]>(`/api/agents/${agentId}/properties`).catch(() => []);
  const suspended = agent.verification_status === "SUSPENDED";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {suspended && (
        <Alert tone="danger" title="This agent is suspended" className="mb-6">
          PropCheck suspended this agent after reviewing complaints. Do not send money to this agent.
        </Alert>
      )}
      <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
            <AgentAvatar name={agent.name} photo={agent.profile_photo_url} size="lg" />
            <div>
              <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">{agent.name}</h1>
              {agent.agency_name && <p className="text-lg text-slate-600">{agent.agency_name}</p>}
              <div className="mt-2 flex flex-wrap gap-2">
                <VerifiedAgentBadge status={agent.verification_status} expiresAt={agent.verification_expiry_date} />
              </div>
              {agent.bio && <p className="mt-4 max-w-2xl whitespace-pre-line text-slate-700">{agent.bio}</p>}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            {[
              { icon: Briefcase, label: "Experience", value: `${agent.years_experience} yrs` },
              { icon: Users, label: "Renters helped", value: agent.completed_connections },
              {
                icon: Star,
                label: "Rating",
                value: agent.average_rating !== null ? `${agent.average_rating.toFixed(1)} (${agent.total_reviews})` : "No reviews",
              },
              { icon: Clock, label: "Usually replies", value: agent.response_time_hours ? `within ${agent.response_time_hours}h` : "—" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
                <s.icon className="size-5 text-brand-600" aria-hidden />
                <p className="mt-2 text-lg font-bold text-slate-900">{s.value}</p>
                <p className="text-xs text-slate-500">{s.label}</p>
              </div>
            ))}
          </div>

          <section>
            <h2 className="mb-1 text-xl font-bold text-slate-900">Listings</h2>
            <p className="mb-4 text-sm text-slate-600">
              A Verified Agent badge does not verify these properties. Check each listing&apos;s own badge.
            </p>
            {listings.length ? (
              <div className="grid gap-5 sm:grid-cols-2">
                {listings.map((p) => (
                  <PropertyCard key={p.id} property={p} />
                ))}
              </div>
            ) : (
              <EmptyState title="No active listings">This agent has no public listings right now.</EmptyState>
            )}
          </section>
        </div>

        <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
          <Card className="p-5">
            <h2 className="font-semibold text-slate-900">Contact</h2>
            {agent.contact_public ? (
              <div className="mt-3 grid gap-2">
                <WhatsAppButton
                  number={agent.whatsapp_number}
                  message={`Hello ${agent.name.split(" ")[0]}, I found your profile on PropCheck Nigeria.`}
                  className="w-full"
                />
                <CallButton number={agent.phone_number} className="w-full" />
                {agent.email && (
                  <a href={`mailto:${agent.email}`} className="text-center text-sm text-brand-700 hover:underline">
                    {agent.email}
                  </a>
                )}
              </div>
            ) : (
              <div className="mt-3 space-y-3 text-sm text-slate-600">
                <p>
                  {suspended
                    ? "Contact details are hidden while this agent is suspended."
                    : "This agent hasn't chosen to show contact details publicly. Ask PropCheck to connect you."}
                </p>
                {!suspended && (
                  <Link href={`/find-an-agent?agent=${agent.id}`} className={buttonClass("primary", "md", "w-full")}>
                    Request help from PropCheck
                  </Link>
                )}
              </div>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-2 font-semibold text-slate-900">Verification</h2>
            <dl className="divide-y divide-slate-100">
              <DefinitionRow label="Status">{humanize(agent.verification_status)}</DefinitionRow>
              <DefinitionRow label="Verified on">{formatDate(agent.verification_date)}</DefinitionRow>
              <DefinitionRow label="Valid until">{formatDate(agent.verification_expiry_date)}</DefinitionRow>
              <DefinitionRow label="Complaints">
                {agent.complaint_status === "NO_OPEN_COMPLAINTS" ? (
                  "None open"
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-700">
                    <ShieldAlert className="size-4" aria-hidden /> {humanize(agent.complaint_status)}
                  </span>
                )}
              </DefinitionRow>
              <DefinitionRow label="On PropCheck since">{formatDate(agent.joined_at)}</DefinitionRow>
            </dl>
          </Card>

          <Card className="p-5">
            <h2 className="mb-2 font-semibold text-slate-900">Coverage</h2>
            <p className="flex items-start gap-1.5 text-sm text-slate-700">
              <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden />
              {[...agent.cities_covered, ...agent.lgas_covered].join(", ") || "—"} ·{" "}
              {agent.states_covered.map(stateLabel).join(", ")}
            </p>
            <p className="mt-2 text-sm text-slate-700">{agent.property_types.map(propertyTypeLabel).join(", ")}</p>
            <p className="mt-2 text-sm text-slate-700">{agent.service_types.map(humanize).join(", ")}</p>
            {(agent.budget_min || agent.budget_max) && (
              <p className="mt-2 text-sm text-slate-700">
                Budget: {formatNaira(agent.budget_min)} – {formatNaira(agent.budget_max)}
              </p>
            )}
          </Card>

          <SafetyWarning />
          <Link href={`/report-problem?agent=${agent.id}`} className="inline-flex items-center gap-1.5 text-sm text-red-700 hover:underline">
            <Flag className="size-4" aria-hidden /> Report this agent
          </Link>
        </aside>
      </div>
    </div>
  );
}
