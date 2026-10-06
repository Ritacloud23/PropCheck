import Link from "next/link";
import { notFound } from "next/navigation";

import { ActionButton } from "@/components/action-button";
import { VerifiedAgentBadge } from "@/components/badges";
import { FeeBreakdown } from "@/components/fee-breakdown";
import { Alert, Card, CardHeader, DefinitionRow, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, formatDateTime, humanize } from "@/lib/format";
import { localMedia } from "@/lib/media";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AuditEntry, PropertyDetail, VerificationCase } from "@/lib/types";

import { ChecklistEditor } from "./checklist-editor";

export default async function ReviewerCaseDetail(props: PageProps<"/dashboard/reviewer/cases/[id]">) {
  const { id } = await props.params;
  if (!/^\d+$/.test(id)) notFound();
  const c = await serverApiOrNull<VerificationCase>(`/api/verification-cases/${id}`);
  if (!c) notFound();
  const [property, audit] = await Promise.all([
    serverApi<PropertyDetail>(`/api/properties/${c.property.id}`),
    serverApi<AuditEntry[]>(`/api/verification-cases/${id}/audit-log`),
  ]);
  const reviewing = c.status === "IN_REVIEW" || c.status === "INSPECTION_BOOKED";
  const t = c.allowed_transitions;
  const base = `/api/verification-cases/${c.id}/transition`;

  return (
    <>
      <PageHeader
        title={c.property.title}
        description={
          <span className="flex flex-wrap items-center gap-2 text-sm">
            <Link href="/dashboard/reviewer/cases" className="text-brand-700 hover:underline">← Cases</Link>
            <span className="font-mono text-slate-600">{c.verification_reference}</span>
            <StatusPill status={c.effective_status} />
          </span>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader
              title="Checklist"
              description={reviewing ? "Results and evidence notes appear on the public report." : "Start the review to edit the checklist."}
            />
            <ChecklistEditor caseId={c.id} checks={c.checks} documents={c.documents} editable={reviewing} />
          </Card>

          <Card>
            <CardHeader title="Supporting documents" description="Uploaded is not trusted. Mark each document after you examine it." />
            <ul className="divide-y divide-slate-100">
              {c.documents.map((d) => (
                <li key={d.id} className="flex flex-col gap-2 px-5 py-4 text-sm sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    <span className="font-medium">#{d.id} {humanize(d.document_type)}</span>
                    <span className="block text-xs text-slate-500">
                      {d.original_filename} · uploaded {formatDate(d.uploaded_at)}
                    </span>
                    {d.link && (
                      <a href={d.link} target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                        Open (private, expires in 10 min)
                      </a>
                    )}
                  </span>
                  <span className="flex flex-wrap items-center gap-2">
                    <StatusPill status={d.review_status} />
                    {reviewing &&
                      (["ACCEPTED", "REVIEWED", "REJECTED"] as const).map((s) => (
                        <ActionButton
                          key={s}
                          path={`/api/verification-cases/${c.id}/documents/${d.id}/review`}
                          body={{ review_status: s }}
                          label={humanize(s)}
                          variant={s === "REJECTED" ? "ghost" : "secondary"}
                          reason={s === "REJECTED" ? { required: false, label: "Notes", field: "reviewer_notes" } : undefined}
                        />
                      ))}
                  </span>
                </li>
              ))}
              {!c.documents.length && <li className="px-5 py-4 text-sm text-slate-500">No documents uploaded.</li>}
            </ul>
          </Card>

          <Card>
            <CardHeader title="Listing as submitted" />
            <div className="grid gap-5 p-5 md:grid-cols-2">
              <div className="space-y-3 text-sm">
                <p>
                  <span className="text-slate-500">Address:</span> {property.address}
                  {property.landmark && ` (${property.landmark})`}, {property.city}, {property.state}
                </p>
                {property.latitude !== null && (
                  <a
                    href={`https://www.openstreetmap.org/?mlat=${property.latitude}&mlon=${property.longitude}#map=17/${property.latitude}/${property.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    Open coordinates in OpenStreetMap
                  </a>
                )}
                <div className="grid grid-cols-3 gap-2">
                  {property.media.slice(0, 6).map((m) => (
                    // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
                    <img key={m.id} src={localMedia(m.url)!} alt={m.caption ?? ""} className="aspect-square w-full rounded-lg object-cover" />
                  ))}
                </div>
              </div>
              <FeeBreakdown fees={property.fees} />
            </div>
          </Card>

          <Card>
            <CardHeader title="Audit log" />
            <ol className="divide-y divide-slate-100 text-sm">
              {audit.map((a) => (
                <li key={a.id} className="px-5 py-3">
                  <span className="font-medium">{humanize(a.action)}</span>
                  {a.to_status && <span className="text-slate-500"> → {humanize(a.to_status)}</span>}
                  <span className="block text-xs text-slate-500">
                    {a.actor_name} · {formatDateTime(a.created_at)}
                    {typeof a.metadata_json.check_type === "string" && ` · ${humanize(a.metadata_json.check_type)}`}
                  </span>
                  {a.reason && <p className="text-slate-600">“{a.reason}”</p>}
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Decision" />
            <div className="space-y-4 p-5">
              <dl className="divide-y divide-slate-100">
                <DefinitionRow label="Submitted by">{c.submitted_by_name}</DefinitionRow>
                <DefinitionRow label="Submitted">{formatDate(c.submitted_at)}</DefinitionRow>
                {c.inspection_scheduled_for && <DefinitionRow label="Inspection">{formatDateTime(c.inspection_scheduled_for)}</DefinitionRow>}
                {c.expires_at && <DefinitionRow label="Expires">{formatDate(c.expires_at)}</DefinitionRow>}
              </dl>
              {c.rejection_reason && <Alert tone="danger">{c.rejection_reason}</Alert>}
              <div className="flex flex-col items-start gap-2">
                {t.includes("IN_REVIEW") && <ActionButton path={base} body={{ to_status: "IN_REVIEW" }} label="Start review" variant="primary" />}
                {t.includes("INSPECTION_BOOKED") && (
                  <ActionButton
                    path={base}
                    body={{ to_status: "INSPECTION_BOOKED" }}
                    label="Book site inspection"
                    dateField={{ name: "inspection_scheduled_for", label: "Inspection date & time", type: "datetime-local", required: true }}
                  />
                )}
                {t.includes("VERIFIED") && (
                  <ActionButton
                    path={base}
                    body={{ to_status: "VERIFIED" }}
                    label="Verify property"
                    variant="primary"
                    reason={{ required: false, label: "Reviewer notes (internal)", field: "reviewer_notes" }}
                    dateField={{ name: "expires_at", label: "Valid until (default 6 months, max 12)" }}
                  />
                )}
                {t.includes("REJECTED") && (
                  <ActionButton
                    path={base}
                    body={{ to_status: "REJECTED" }}
                    label="Reject"
                    variant="danger"
                    reason={{ required: true, label: "Reason (shown on the public report)" }}
                  />
                )}
                {t.includes("EXPIRED") && (
                  <ActionButton path={base} body={{ to_status: "EXPIRED" }} label="Mark expired" reason={{ required: false }} />
                )}
              </div>
            </div>
          </Card>
          {c.listing_agent && (
            <Card className="p-5 text-sm">
              <p className="text-slate-500">Listing agent</p>
              <Link href={`/dashboard/reviewer/agents/${c.listing_agent.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
                {c.listing_agent.name}
              </Link>
              <div className="mt-1">
                <VerifiedAgentBadge status={c.listing_agent.verification_status} expiresAt={c.listing_agent.verification_expiry_date} />
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
