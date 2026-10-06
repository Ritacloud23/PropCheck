import { Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, humanize } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Report } from "@/lib/types";

export default async function RenterReports() {
  const reports = await serverApi<Report[]>("/api/reports/mine");
  return (
    <>
      <PageHeader title="My reports" description="Reports you've filed about agents or listings, and what PropCheck decided." />
      {!reports.length ? (
        <EmptyState title="You haven't filed any reports">Use “Report” on an agent profile or listing if something is wrong.</EmptyState>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-slate-900">{humanize(r.reason)}</p>
                  <p className="text-sm text-slate-600">
                    {r.property ? r.property.title : r.agent_name} · filed {formatDate(r.created_at)}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </div>
              <p className="mt-3 text-sm text-slate-700">{r.description}</p>
              {r.resolution_reason && (
                <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <span className="font-medium">PropCheck decision:</span> {r.resolution_reason}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
