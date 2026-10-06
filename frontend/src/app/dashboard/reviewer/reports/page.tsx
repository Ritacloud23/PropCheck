import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { StatusTabs } from "@/components/status-tabs";
import { Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDateTime, humanize } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Report } from "@/lib/types";

import { ReportDecision } from "./report-decision";

const TABS = ["OPEN", "IN_REVIEW", "RESOLVED", "REJECTED"];

export default async function ReviewerReports(props: PageProps<"/dashboard/reviewer/reports">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : "OPEN";
  const reports = await serverApi<Report[]>(`/api/reviewer/reports?status=${current}`);
  return (
    <>
      <PageHeader title="Reports" description="Complaints about agents and listings. Resolving can suspend an agent in the same step." />
      <StatusTabs basePath="/dashboard/reviewer/reports" options={TABS} current={current} />
      {!reports.length ? (
        <EmptyState title="No reports here" />
      ) : (
        <div className="space-y-4">
          {reports.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="text-sm">
                  <p className="font-semibold text-slate-900">{humanize(r.reason)}</p>
                  <p className="text-slate-600">
                    From {r.reporter_name} · {formatDateTime(r.created_at)}
                  </p>
                  <p className="mt-1 text-slate-600">
                    {r.agent_id && (
                      <>
                        Agent:{" "}
                        <Link href={`/dashboard/reviewer/agents/${r.agent_id}`} className="text-brand-700 hover:underline">
                          {r.agent_name}
                        </Link>
                      </>
                    )}
                    {r.property && (
                      <>
                        {r.agent_id && " · "}Listing:{" "}
                        <Link href={`/properties/${r.property.public_slug}`} className="text-brand-700 hover:underline">
                          {r.property.title}
                        </Link>
                      </>
                    )}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </div>
              <p className="mt-3 whitespace-pre-line text-sm text-slate-800">{r.description}</p>
              {r.evidence_link && (
                <a href={r.evidence_link} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-medium text-brand-700 hover:underline">
                  Open evidence (private)
                </a>
              )}
              {r.resolution_reason && <p className="mt-3 text-sm text-slate-600">Decision: {r.resolution_reason}</p>}
              {r.reviewer_notes && <p className="text-sm text-slate-500">Notes: {r.reviewer_notes}</p>}
              {(r.status === "OPEN" || r.status === "IN_REVIEW") && (
                <div className="mt-4 space-y-3">
                  {r.status === "OPEN" && <ActionButton path={`/api/reviewer/reports/${r.id}/start-review`} label="Start review" />}
                  <ReportDecision reportId={r.id} canSuspend={!!r.agent_id} />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
