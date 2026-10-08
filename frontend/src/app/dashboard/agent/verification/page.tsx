import Link from "next/link";

import { VerifiedPropertyBadge } from "@/components/badges";
import { Alert, Card, CardHeader, EmptyState, PageHeader } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { requireRole } from "@/lib/guards";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AgentPrivate, VerificationCase } from "@/lib/types";

import { AgentVerificationCard } from "./agent-verification-card";

export default async function AgentVerificationPage() {
  const user = await requireRole("AGENT", "LANDLORD");
  const [profile, cases] = await Promise.all([
    serverApiOrNull<AgentPrivate>("/api/agents/profile"),
    serverApi<VerificationCase[]>("/api/verification-cases"),
  ]);
  return (
    <>
      <PageHeader
        title="Verification"
        description="Agent verification and property verification are separate. A Verified Agent badge does not verify your listings."
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader title="Property verification cases" description="Start a case from a listing's page. Reviewers who manage a listing can never decide its case." />
          {!cases.length ? (
            <div className="p-5">
              <EmptyState
                title="No verification cases yet"
                action={
                  <Link href="/dashboard/agent/properties" className="text-sm font-semibold text-brand-700 hover:underline">
                    Go to my listings
                  </Link>
                }
              >
                Open a listing, upload its photos and authority documents, then submit it for verification.
              </EmptyState>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {cases.map((c) => (
                <li key={c.id} className="flex flex-wrap items-start justify-between gap-3 p-5 text-sm">
                  <div>
                    <Link href={`/dashboard/agent/properties/${c.property.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
                      {c.property.title}
                    </Link>
                    <p className="text-slate-600">
                      Ref {c.verification_reference}
                      {c.submitted_at && <> · submitted {formatDate(c.submitted_at)}</>}
                      {c.expires_at && c.effective_status === "VERIFIED" && <> · expires {formatDate(c.expires_at)}</>}
                    </p>
                    {c.rejection_reason && <p className="mt-1 text-red-700">Rejected: {c.rejection_reason}</p>}
                  </div>
                  <VerifiedPropertyBadge status={c.effective_status} expiresAt={c.expires_at} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <div className="space-y-6">
          {user.role === "AGENT" || profile ? (
            <AgentVerificationCard profile={profile} />
          ) : (
            <Alert tone="info">Landlords don&apos;t need a Verified Agent badge. Your listings can still be verified.</Alert>
          )}
        </div>
      </div>
    </>
  );
}
