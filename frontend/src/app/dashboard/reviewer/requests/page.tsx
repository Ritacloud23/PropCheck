import Link from "next/link";

import { StatusTabs } from "@/components/status-tabs";
import { Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, formatNaira, propertyTypeLabel, stateLabel } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { HouseSearchRequest } from "@/lib/types";

const TABS = ["WAITING", "ASSIGNED", "CONTACTED", "COMPLETED", "CANCELLED"];

export default async function ReviewerRequests(props: PageProps<"/dashboard/reviewer/requests">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : undefined;
  let requests = await serverApi<HouseSearchRequest[]>(
    `/api/house-search-requests${current && current !== "WAITING" ? `?status=${current}` : ""}`,
  );
  if (!current || current === "WAITING") requests = requests.filter((r) => r.status === "SUBMITTED" || r.status === "MATCHING");
  return (
    <>
      <PageHeader title="House-search matching" description="Assign each renter to one verified agent who covers their area." />
      <StatusTabs basePath="/dashboard/reviewer/requests" options={TABS} current={current} />
      {!requests.length ? (
        <EmptyState title="No requests in this queue" />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {requests.map((r) => (
              <li key={r.id}>
                <Link href={`/dashboard/reviewer/requests/${r.id}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-slate-50">
                  <div className="text-sm">
                    <p className="font-semibold text-slate-900">
                      {r.name} · {propertyTypeLabel(r.property_type)} in {r.city}, {stateLabel(r.state)}
                    </p>
                    <p className="text-slate-600">
                      {formatNaira(r.budget_min)} – {formatNaira(r.budget_max)} · {formatDate(r.created_at)}
                    </p>
                  </div>
                  <StatusPill status={r.status} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
