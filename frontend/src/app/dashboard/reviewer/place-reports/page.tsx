import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { StatusTabs } from "@/components/status-tabs";
import { Card, EmptyState, PageHeader, Pill, StatusPill } from "@/components/ui";
import { formatDateTime, humanize, PLACE_CATEGORY_LABELS } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { PlaceReport } from "@/lib/types";

const TABS = ["OPEN", "RESOLVED", "REJECTED"];

export default async function PlaceReportsPage(props: PageProps<"/dashboard/reviewer/place-reports">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : "OPEN";
  const reports = await serverApi<PlaceReport[]>(`/api/reviewer/place-reports?status=${current}`);
  return (
    <>
      <PageHeader
        title="Nearby place reports"
        description="Users flag wrong locations, hours or closed places. Resolve and hide the place until it is corrected, or reject the report."
      />
      <StatusTabs basePath="/dashboard/reviewer/place-reports" options={TABS} current={current} />
      {!reports.length ? (
        <EmptyState title="No reports here" />
      ) : (
        <div className="space-y-3">
          {reports.map((r) => {
            const base = `/api/reviewer/place-reports/${r.id}`;
            return (
              <Card key={r.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3 text-sm">
                  <div>
                    <p className="font-semibold text-slate-900">
                      {r.place_name}{" "}
                      <span className="font-normal text-slate-500">
                        · {PLACE_CATEGORY_LABELS[r.place_category].one} · {r.place_area ? `${r.place_area}, ` : ""}
                        {r.place_city}
                      </span>
                    </p>
                    <p className="text-slate-600">
                      {humanize(r.reason)} · reported by {r.reporter_name} · {formatDateTime(r.created_at)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {r.place_is_active === false && <Pill tone="danger">Hidden</Pill>}
                    <StatusPill status={r.status} />
                  </div>
                </div>
                {r.description && <p className="mt-3 text-sm text-slate-800">“{r.description}”</p>}
                {r.reviewer_notes && <p className="mt-2 text-sm text-slate-500">Notes: {r.reviewer_notes}</p>}
                {r.status === "OPEN" && (
                  <div className="mt-4 flex flex-wrap items-start gap-2">
                    <ActionButton path={`${base}/resolve`} label="Resolve" variant="primary" reason={{ required: true, label: "What was done?" }} />
                    <ActionButton
                      path={`${base}/resolve`}
                      body={{ deactivate_place: true }}
                      label="Resolve & hide place"
                      variant="danger"
                      reason={{ required: true, label: "Why hide this place?" }}
                    />
                    <ActionButton path={`${base}/reject`} label="Reject" variant="ghost" reason={{ required: true, label: "Why is the report wrong?" }} />
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
      <p className="mt-6 text-sm text-slate-500">
        Places can be checked on the{" "}
        <Link href="/nearby" className="text-brand-700 hover:underline">
          nearby page
        </Link>
        .
      </p>
    </>
  );
}
