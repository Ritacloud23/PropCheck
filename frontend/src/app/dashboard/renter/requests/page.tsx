import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { VerifiedAgentBadge } from "@/components/badges";
import { Card, EmptyState, PageHeader, StatusPill, buttonClass } from "@/components/ui";
import { CallButton, WhatsAppButton } from "@/components/whatsapp-button";
import { formatDate, formatDateTime, formatNaira, propertyTypeLabel, stateLabel } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { HouseSearchRequest } from "@/lib/types";

export default async function RenterRequests() {
  const requests = await serverApi<HouseSearchRequest[]>("/api/house-search-requests");
  return (
    <>
      <PageHeader
        title="House-search requests"
        description="Each request is shared only with the one verified agent PropCheck assigns."
        action={
          <Link href="/find-an-agent" className={buttonClass("primary", "md")}>
            New request
          </Link>
        }
      />
      {!requests.length ? (
        <EmptyState title="No requests yet" action={<Link href="/find-an-agent" className={buttonClass("primary", "md")}>Ask for help</Link>}>
          Tell us what you&apos;re looking for and we&apos;ll match you with a verified agent.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {requests.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900">
                    {r.bedrooms > 0 ? `${r.bedrooms}-bed ` : ""}
                    {propertyTypeLabel(r.property_type)} in {r.city}, {stateLabel(r.state)}
                  </p>
                  <p className="text-sm text-slate-600">
                    {formatNaira(r.budget_min)} – {formatNaira(r.budget_max)} · {r.purpose === "RENT" ? "Rent" : "Buy"} · sent{" "}
                    {formatDate(r.created_at)}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </div>
              {r.assigned_agent && (
                <div className="mt-4 rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Your assigned agent</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <Link href={`/agents/${r.assigned_agent.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
                      {r.assigned_agent.name}
                    </Link>
                    <VerifiedAgentBadge status={r.assigned_agent.verification_status} expiresAt={r.assigned_agent.verification_expiry_date} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <WhatsAppButton
                      number={r.assigned_agent.whatsapp_number}
                      message={`Hello, PropCheck matched us for my request #${r.id} (${r.city}).`}
                    />
                    <CallButton number={r.assigned_agent.phone_number} />
                  </div>
                </div>
              )}
              {r.enquiries.filter((e) => e.message).map((e) => (
                <blockquote key={e.id} className="mt-3 border-l-4 border-brand-600 pl-3 text-sm text-slate-700">
                  “{e.message}”
                  <span className="block text-xs text-slate-500">
                    {e.agent_name} · {formatDateTime(e.responded_at)}
                  </span>
                </blockquote>
              ))}
              {r.cancellation_reason && <p className="mt-3 text-sm text-slate-500">Cancelled: {r.cancellation_reason}</p>}
              <div className="mt-4 flex flex-wrap gap-2">
                {r.allowed_actions.includes("COMPLETED") && (
                  <ActionButton path={`/api/house-search-requests/${r.id}/complete`} label="I found a place" variant="primary" />
                )}
                {r.allowed_actions.includes("CANCELLED") && (
                  <ActionButton
                    path={`/api/house-search-requests/${r.id}/cancel`}
                    label="Cancel request"
                    variant="ghost"
                    reason={{ required: false, label: "Why are you cancelling? (optional)" }}
                  />
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
