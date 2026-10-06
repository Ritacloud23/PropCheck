import type { Metadata } from "next";
import Link from "next/link";

import { Card, PageHeader, buttonClass } from "@/components/ui";
import { getCurrentUser, getReference, serverApiOrNull } from "@/lib/server-api";
import type { AgentPublic, PropertyDetail } from "@/lib/types";

import { ReportForm } from "./report-form";

export const metadata: Metadata = { title: "Report a problem" };

export default async function ReportProblemPage(props: PageProps<"/report-problem">) {
  const sp = await props.searchParams;
  const agentId = typeof sp.agent === "string" && /^\d+$/.test(sp.agent) ? sp.agent : null;
  const propertyId = typeof sp.property === "string" && /^\d+$/.test(sp.property) ? sp.property : null;
  const [user, reference] = await Promise.all([getCurrentUser(), getReference()]);

  let target: { kind: "agent" | "property"; id: number; name: string } | null = null;
  if (propertyId) {
    const p = await serverApiOrNull<PropertyDetail>(`/api/properties/${propertyId}`);
    if (p) target = { kind: "property", id: p.id, name: p.title };
  } else if (agentId) {
    const a = await serverApiOrNull<AgentPublic>(`/api/agents/${agentId}`);
    if (a) target = { kind: "agent", id: a.id, name: a.agency_name ? `${a.name} (${a.agency_name})` : a.name };
  }
  const here = `/report-problem${propertyId ? `?property=${propertyId}` : agentId ? `?agent=${agentId}` : ""}`;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Report a problem"
        description="Fake identity, misleading photos, surprise fees, pressure to pay before inspection — tell us. Reports are reviewed by a person and can lead to an agent being suspended."
      />
      {!user ? (
        <Card className="p-6 text-center">
          <p className="font-semibold text-slate-900">Please log in to file a report</p>
          <p className="mt-1 text-sm text-slate-600">This lets us follow up with you and prevents abuse of the reporting system.</p>
          <div className="mt-5 flex justify-center gap-2">
            <Link href={`/login?next=${encodeURIComponent(here)}`} className={buttonClass("secondary", "md")}>
              Log in
            </Link>
            <Link href="/register" className={buttonClass("primary", "md")}>
              Create account
            </Link>
          </div>
        </Card>
      ) : target ? (
        <ReportForm target={target} reasons={reference.report_reasons} />
      ) : (
        <Card className="p-6 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">Which agent or listing is this about?</p>
          <p className="mt-2">
            Open the agent&apos;s profile or the property listing and use the <strong>Report</strong> link at the bottom of the
            page, so your report is attached to the right record.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Link href="/agents" className={buttonClass("secondary", "md")}>
              Browse agents
            </Link>
            <Link href="/properties" className={buttonClass("secondary", "md")}>
              Browse properties
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
