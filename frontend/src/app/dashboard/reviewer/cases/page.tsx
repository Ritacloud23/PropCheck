import Link from "next/link";

import { StatusTabs } from "@/components/status-tabs";
import { Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, stateLabel } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { VerificationCase } from "@/lib/types";

const TABS = ["WAITING", "SUBMITTED", "IN_REVIEW", "INSPECTION_BOOKED", "VERIFIED", "REJECTED", "EXPIRED"];
const WAITING = ["SUBMITTED", "IN_REVIEW", "INSPECTION_BOOKED"];

export default async function ReviewerCases(props: PageProps<"/dashboard/reviewer/cases">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : undefined;
  const query = current && current !== "WAITING" ? `?status=${current}` : "";
  let cases = await serverApi<VerificationCase[]>(`/api/verification-cases${query}`);
  if (!query) cases = cases.filter((c) => WAITING.includes(c.status));
  return (
    <>
      <PageHeader title="Property verification cases" />
      <StatusTabs basePath="/dashboard/reviewer/cases" options={TABS} current={current} />
      {!cases.length ? (
        <EmptyState title="No cases in this queue" />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {cases.map((c) => {
              const done = c.checks.filter((x) => x.result !== "NOT_STARTED").length;
              return (
                <li key={c.id}>
                  <Link href={`/dashboard/reviewer/cases/${c.id}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-slate-50">
                    <div className="text-sm">
                      <p className="font-semibold text-slate-900">{c.property.title}</p>
                      <p className="text-slate-600">
                        <span className="font-mono">{c.verification_reference}</span> · {c.property.city}, {stateLabel(c.property.state)} · submitted{" "}
                        {formatDate(c.submitted_at)} by {c.submitted_by_name} · checklist {done}/{c.checks.length}
                      </p>
                    </div>
                    <StatusPill status={c.effective_status} />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </>
  );
}
