import Link from "next/link";

import { Alert, PageHeader } from "@/components/ui";
import { serverApi } from "@/lib/server-api";

type Summary = {
  agent_applications_waiting: number;
  property_cases_waiting: number;
  house_search_unassigned: number;
  open_reports: number;
  open_place_reports: number;
  refund_requests: number;
};

export default async function ReviewerHome() {
  const s = await serverApi<Summary>("/api/reviewer/summary");
  const tiles = [
    { label: "Agent applications", value: s.agent_applications_waiting, href: "/dashboard/reviewer/agents" },
    { label: "Property cases", value: s.property_cases_waiting, href: "/dashboard/reviewer/cases" },
    { label: "Renters to match", value: s.house_search_unassigned, href: "/dashboard/reviewer/requests" },
    { label: "Open reports", value: s.open_reports, href: "/dashboard/reviewer/reports" },
    { label: "Nearby place reports", value: s.open_place_reports, href: "/dashboard/reviewer/place-reports" },
    { label: "Refund requests", value: s.refund_requests, href: "/dashboard/reviewer/reservations" },
  ];
  return (
    <>
      <PageHeader title="Review queue" description="Everything waiting for a human decision." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {tiles.map((t) => (
          <Link key={t.label} href={t.href} className="rounded-xl bg-white p-5 ring-1 ring-slate-200 hover:ring-brand-600">
            <p className={`text-3xl font-bold ${t.value ? "text-amber-700" : "text-slate-900"}`}>{t.value}</p>
            <p className="text-sm text-slate-600">{t.label}</p>
          </Link>
        ))}
      </div>
      <Alert tone="info" className="mt-6">
        You can&apos;t review an application or case you submitted, or a property you own or list. The system blocks it and
        every decision is written to the audit log.
      </Alert>
    </>
  );
}
