import { Alert, Card, CardHeader, DefinitionRow, StatusPill } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { AgentPrivate } from "@/lib/types";

import { VerificationUpload } from "../profile/profile-form";

/** Status of the agent's own Verified Agent application, with the upload form when they may (re)apply. */
export function AgentVerificationCard({ profile }: { profile: AgentPrivate | null }) {
  const app = profile?.latest_application ?? null;
  const canApply = profile && (!app || ["REJECTED", "EXPIRED"].includes(app.status) || profile.verification_status === "EXPIRED");
  return (
    <Card>
      <CardHeader title="Agent verification" />
      <div className="space-y-4 p-5">
        {!profile ? (
          <p className="text-sm text-slate-600">Create your profile first.</p>
        ) : (
          <>
            {app && (
              <dl className="divide-y divide-slate-100">
                <DefinitionRow label="Status">
                  <StatusPill status={app.status} />
                </DefinitionRow>
                <DefinitionRow label="Submitted">{formatDate(app.submitted_at)}</DefinitionRow>
                {app.verified_at && <DefinitionRow label="Verified">{formatDate(app.verified_at)}</DefinitionRow>}
                {app.expires_at && <DefinitionRow label="Expires">{formatDate(app.expires_at)}</DefinitionRow>}
                <DefinitionRow label="ID document">
                  {app.identity_document_link ? (
                    <a href={app.identity_document_link} target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                      View (private link)
                    </a>
                  ) : (
                    "—"
                  )}
                </DefinitionRow>
              </dl>
            )}
            {app?.rejection_reason && (
              <Alert tone={app.status === "SUSPENDED" ? "danger" : "warning"} title={app.status === "SUSPENDED" ? "Suspended" : "Not approved"}>
                {app.rejection_reason}
              </Alert>
            )}
            {profile.verification_status === "SUSPENDED" && (
              <Alert tone="danger">Your profile is hidden from the directory and you cannot create listings while suspended.</Alert>
            )}
            {canApply ? (
              <VerificationUpload />
            ) : app && ["SUBMITTED", "IN_REVIEW"].includes(app.status) ? (
              <p className="text-sm text-slate-600">A reviewer is checking your documents. You&apos;ll be notified of the outcome.</p>
            ) : null}
          </>
        )}
      </div>
    </Card>
  );
}
