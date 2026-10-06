import Link from "next/link";
import { notFound } from "next/navigation";

import { ActionButton } from "@/components/action-button";
import { VerifiedAgentBadge } from "@/components/badges";
import { Card, CardHeader, DefinitionRow, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, formatNaira, formatNgPhone, humanize, propertyTypeLabel, stateLabel } from "@/lib/format";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AgentPublic, HouseSearchRequest } from "@/lib/types";

export default async function ReviewerRequestDetail(props: PageProps<"/dashboard/reviewer/requests/[id]">) {
  const { id } = await props.params;
  if (!/^\d+$/.test(id)) notFound();
  const r = await serverApiOrNull<HouseSearchRequest>(`/api/house-search-requests/${id}`);
  if (!r) notFound();
  const canAssign = r.status === "SUBMITTED" || r.status === "MATCHING";
  const candidates = canAssign ? await serverApi<AgentPublic[]>(`/api/house-search-requests/${id}/candidate-agents`) : [];

  return (
    <>
      <PageHeader
        title={`Request #${r.id}`}
        description={<Link href="/dashboard/reviewer/requests" className="text-sm text-brand-700 hover:underline">← All requests</Link>}
      />
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <Card className="h-fit">
          <CardHeader title={r.name} action={<StatusPill status={r.status} />} />
          <dl className="divide-y divide-slate-100 px-5">
            <DefinitionRow label="Phone">{formatNgPhone(r.phone)}</DefinitionRow>
            <DefinitionRow label="Looking for">
              {r.bedrooms > 0 ? `${r.bedrooms}-bed ` : ""}
              {propertyTypeLabel(r.property_type)} ({r.purpose === "RENT" ? "rent" : "buy"})
            </DefinitionRow>
            <DefinitionRow label="Where">
              {r.city}, {stateLabel(r.state)}
            </DefinitionRow>
            <DefinitionRow label="Budget">
              {formatNaira(r.budget_min)} – {formatNaira(r.budget_max)}
            </DefinitionRow>
            <DefinitionRow label="Furnishing">{humanize(r.furnished_preference)}</DefinitionRow>
            <DefinitionRow label="Move in">{formatDate(r.preferred_move_in_date)}</DefinitionRow>
            <DefinitionRow label="Consent to share">{r.consent_to_share ? "Yes" : "No"}</DefinitionRow>
          </dl>
          {r.description && <p className="px-5 pb-5 text-sm text-slate-700">“{r.description}”</p>}
          {r.status === "SUBMITTED" && (
            <div className="px-5 pb-5">
              <ActionButton path={`/api/house-search-requests/${r.id}/matching`} label="Mark as matching" />
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title={canAssign ? "Candidate agents" : "Assigned agent"}
            description={canAssign ? "Currently verified agents covering this state, best coverage match first." : undefined}
          />
          {canAssign ? (
            candidates.length ? (
              <ul className="divide-y divide-slate-100">
                {candidates.map((a) => (
                  <li key={a.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-sm">
                      <p className="font-semibold text-slate-900">
                        {a.name} {a.agency_name && <span className="font-normal text-slate-500">· {a.agency_name}</span>}
                      </p>
                      <p className="text-slate-600">
                        {a.cities_covered.includes(r.city) ? "✓ covers " + r.city : "Covers " + (a.cities_covered.slice(0, 3).join(", ") || stateLabel(r.state))} ·{" "}
                        {a.property_types.includes(r.property_type) ? "✓ " : ""}
                        {propertyTypeLabel(r.property_type)} · {a.years_experience} yrs
                      </p>
                    </div>
                    <ActionButton
                      path={`/api/house-search-requests/${r.id}/assign`}
                      body={{ agent_id: a.id }}
                      label="Assign"
                      variant="primary"
                      reason={{ required: false, label: "Note for the audit log (optional)", field: "note" }}
                    />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-5">
                <EmptyState title="No verified agents cover this area yet" />
              </div>
            )
          ) : r.assigned_agent ? (
            <div className="space-y-2 p-5 text-sm">
              <p className="font-semibold text-slate-900">{r.assigned_agent.name}</p>
              <VerifiedAgentBadge status={r.assigned_agent.verification_status} expiresAt={r.assigned_agent.verification_expiry_date} />
              {r.enquiries.map((e) => (
                <p key={e.id} className="text-slate-600">
                  Enquiry: {humanize(e.status)} {e.message && `— “${e.message}”`}
                </p>
              ))}
            </div>
          ) : (
            <p className="p-5 text-sm text-slate-600">{r.cancellation_reason ? `Cancelled: ${r.cancellation_reason}` : "Not assigned."}</p>
          )}
        </Card>
      </div>
    </>
  );
}
