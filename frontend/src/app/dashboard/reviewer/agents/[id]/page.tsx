import Link from "next/link";
import { notFound } from "next/navigation";

import { ActionButton } from "@/components/action-button";
import { AgentAvatar } from "@/components/agent-card";
import { VerifiedAgentBadge } from "@/components/badges";
import { Alert, Card, CardHeader, DefinitionRow, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, formatNgPhone, humanize, stateLabel } from "@/lib/format";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AgentApplication, AuditEntry, ReviewerAgent } from "@/lib/types";

export default async function ReviewerAgentDetail(props: PageProps<"/dashboard/reviewer/agents/[id]">) {
  const { id } = await props.params;
  if (!/^\d+$/.test(id)) notFound();
  const agent = await serverApiOrNull<ReviewerAgent>(`/api/reviewer/agents/${id}`);
  if (!agent) notFound();
  const app: AgentApplication | null = agent.latest_application;
  const history = app
    ? await serverApi<AuditEntry[]>(`/api/reviewer/audit-log?entity_type=AgentVerification&entity_id=${app.id}`)
    : [];
  const base = `/api/reviewer/agents/${agent.id}`;
  const actions = agent.allowed_actions;

  return (
    <>
      <PageHeader
        title={agent.name}
        description={<Link href="/dashboard/reviewer/agents" className="text-sm text-brand-700 hover:underline">← All applications</Link>}
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Card className="p-5">
            <div className="flex items-start gap-4">
              <AgentAvatar name={agent.name} photo={agent.profile_photo_url} />
              <div className="min-w-0">
                <p className="font-semibold text-slate-900">{agent.agency_name ?? "Independent agent"}</p>
                <VerifiedAgentBadge status={agent.verification_status} expiresAt={agent.verification_expiry_date} />
                <p className="mt-2 text-sm text-slate-700">{agent.bio || "No bio."}</p>
              </div>
            </div>
            <dl className="mt-4 grid divide-y divide-slate-100 sm:grid-cols-2 sm:divide-y-0">
              <DefinitionRow label="Account email">{agent.account_email}</DefinitionRow>
              <DefinitionRow label="Phone">{formatNgPhone(agent.private_phone_number)}</DefinitionRow>
              <DefinitionRow label="States">{agent.states_covered.map(stateLabel).join(", ")}</DefinitionRow>
              <DefinitionRow label="Areas">{agent.cities_covered.join(", ") || "—"}</DefinitionRow>
              <DefinitionRow label="Experience">{agent.years_experience} yrs</DefinitionRow>
              <DefinitionRow label="Open reports">{agent.open_reports}</DefinitionRow>
            </dl>
          </Card>

          <Card>
            <CardHeader title="Evidence" description="Private documents. Links expire after 10 minutes — reload to get fresh ones." />
            <div className="space-y-3 p-5 text-sm">
              {!app ? (
                <p className="text-slate-600">No application submitted.</p>
              ) : (
                <>
                  <div className="flex flex-wrap gap-3">
                    {app.identity_document_link && (
                      <a href={app.identity_document_link} target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 hover:underline">
                        Open government ID
                      </a>
                    )}
                    {app.business_document_link && (
                      <a href={app.business_document_link} target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 hover:underline">
                        Open business document
                      </a>
                    )}
                  </div>
                  {app.evidence_notes && <p className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">Agent note: {app.evidence_notes}</p>}
                  {app.reviewer_notes && <p className="text-slate-600">Reviewer notes: {app.reviewer_notes}</p>}
                  {app.rejection_reason && <Alert tone="warning">{app.rejection_reason}</Alert>}
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="History" />
            <ol className="divide-y divide-slate-100 text-sm">
              {history.map((h) => (
                <li key={h.id} className="px-5 py-3">
                  <span className="font-medium">{humanize(h.action)}</span>{" "}
                  <span className="text-slate-500">
                    by {h.actor_name} · {formatDate(h.created_at)}
                  </span>
                  {h.reason && <p className="text-slate-600">“{h.reason}”</p>}
                </li>
              ))}
              {!history.length && <li className="px-5 py-3 text-slate-500">No history.</li>}
            </ol>
          </Card>
        </div>

        <Card className="h-fit">
          <CardHeader title="Decision" />
          <div className="space-y-4 p-5">
            {app && (
              <dl className="divide-y divide-slate-100">
                <DefinitionRow label="Application">
                  <StatusPill status={app.status} />
                </DefinitionRow>
                <DefinitionRow label="Submitted">{formatDate(app.submitted_at)}</DefinitionRow>
                {app.expires_at && <DefinitionRow label="Expires">{formatDate(app.expires_at)}</DefinitionRow>}
              </dl>
            )}
            {!actions.length && (
              <p className="text-sm text-slate-600">
                No actions available{app && ["SUBMITTED", "IN_REVIEW"].includes(app.status) ? " (you may have a conflict of interest)" : ""}.
              </p>
            )}
            <div className="flex flex-col items-start gap-2">
              {actions.includes("start-review") && <ActionButton path={`${base}/start-review`} label="Start review" variant="primary" />}
              {actions.includes("approve") && (
                <ActionButton
                  path={`${base}/approve`}
                  label="Approve (Verified Agent)"
                  variant="primary"
                  reason={{ required: false, label: "Reviewer notes (optional)", field: "reviewer_notes" }}
                  dateField={{ name: "expires_at", label: "Expiry date (default 12 months)" }}
                />
              )}
              {actions.includes("reject") && (
                <ActionButton path={`${base}/reject`} label="Reject" variant="danger" reason={{ required: true, label: "Reason shown to the agent" }} />
              )}
              {actions.includes("suspend") && (
                <ActionButton path={`${base}/suspend`} label="Suspend" variant="danger" reason={{ required: true, label: "Reason for suspension" }} />
              )}
              {actions.includes("expire") && <ActionButton path={`${base}/expire`} label="Mark expired" confirm="Mark this verification as expired?" />}
              {actions.includes("reinstate") && <ActionButton path={`${base}/reinstate`} label="Re-open review" />}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
