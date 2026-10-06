import { ActionButton } from "@/components/action-button";
import { Alert, Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { CallButton, WhatsAppButton } from "@/components/whatsapp-button";
import { formatDate, formatNaira, humanize, propertyTypeLabel, stateLabel } from "@/lib/format";
import { requireRole } from "@/lib/guards";
import { serverApi } from "@/lib/server-api";
import type { AgentEnquiry } from "@/lib/types";

export default async function AgentEnquiries() {
  const user = await requireRole("AGENT", "LANDLORD");
  if (user.role !== "AGENT") {
    return <Alert tone="info">Renter matching is only available to agent accounts.</Alert>;
  }
  const enquiries = await serverApi<AgentEnquiry[]>("/api/agent/enquiries");
  return (
    <>
      <PageHeader
        title="Matched renters"
        description="PropCheck assigned these renters to you. They consented to share their details with you only — please don't pass them on."
      />
      {!enquiries.length ? (
        <EmptyState title="No matched renters yet">Keep your coverage areas up to date and stay verified to receive matches.</EmptyState>
      ) : (
        <div className="space-y-4">
          {enquiries.map(({ id, request: r, message, status }) => (
            <Card key={id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900">
                    {r.name} · {r.bedrooms > 0 ? `${r.bedrooms}-bed ` : ""}
                    {propertyTypeLabel(r.property_type)} in {r.city}, {stateLabel(r.state)}
                  </p>
                  <p className="text-sm text-slate-600">
                    {formatNaira(r.budget_min)} – {formatNaira(r.budget_max)} · {humanize(r.furnished_preference)} · move in{" "}
                    {formatDate(r.preferred_move_in_date)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <StatusPill status={status} />
                  <StatusPill status={r.status} />
                </div>
              </div>
              {r.description && <p className="mt-3 text-sm text-slate-700">“{r.description}”</p>}
              <div className="mt-3 flex flex-wrap gap-2">
                <WhatsAppButton number={r.whatsapp_number ?? r.phone} message={`Hello ${r.name.split(" ")[0]}, PropCheck matched us for your house search in ${r.city}.`} />
                <CallButton number={r.phone} />
              </div>
              {message && <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">Your reply: {message}</p>}
              <div className="mt-4 flex flex-wrap items-start gap-2">
                {status !== "CLOSED" && ["ASSIGNED", "CONTACTED"].includes(r.status) && (
                  <ActionButton
                    path={`/api/house-search-requests/${r.id}/respond`}
                    label={message ? "Send another update" : "Reply to renter"}
                    variant="primary"
                    reason={{ required: true, label: "Message to the renter (shown in their dashboard)", field: "message" }}
                  />
                )}
                {r.allowed_actions.includes("CONTACTED") && (
                  <ActionButton path={`/api/house-search-requests/${r.id}/contacted`} label="Mark as contacted" />
                )}
                {r.allowed_actions.includes("COMPLETED") && (
                  <ActionButton path={`/api/house-search-requests/${r.id}/complete`} label="Mark completed" />
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
