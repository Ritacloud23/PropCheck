import Link from "next/link";

import { VerifiedAgentBadge } from "@/components/badges";
import { StatusTabs } from "@/components/status-tabs";
import { Card, EmptyState, PageHeader } from "@/components/ui";
import { formatDate, stateLabel } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { ReviewerAgent } from "@/lib/types";

const TABS = ["WAITING", "VERIFIED", "SUSPENDED", "REJECTED", "EXPIRED"];

export default async function ReviewerAgents(props: PageProps<"/dashboard/reviewer/agents">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : undefined;
  const agents = await serverApi<ReviewerAgent[]>(`/api/reviewer/agents${current && current !== "WAITING" ? `?status=${current}` : ""}`);
  return (
    <>
      <PageHeader title="Agent applications" />
      <StatusTabs basePath="/dashboard/reviewer/agents" options={TABS} current={current} />
      {!agents.length ? (
        <EmptyState title="Nothing here" />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {agents.map((a) => (
              <li key={a.id}>
                <Link href={`/dashboard/reviewer/agents/${a.id}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-slate-50">
                  <div className="text-sm">
                    <p className="font-semibold text-slate-900">
                      {a.name} {a.agency_name && <span className="font-normal text-slate-500">· {a.agency_name}</span>}
                    </p>
                    <p className="text-slate-600">
                      {a.states_covered.map(stateLabel).join(", ")} · submitted {formatDate(a.latest_application?.submitted_at)}
                      {a.open_reports > 0 && <span className="ml-2 font-medium text-red-700">{a.open_reports} open report(s)</span>}
                    </p>
                  </div>
                  <VerifiedAgentBadge status={a.verification_status} expiresAt={a.verification_expiry_date} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
