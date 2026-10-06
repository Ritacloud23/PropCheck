import Link from "next/link";

import { AgentAvatar } from "@/components/agent-card";
import { VerifiedAgentBadge } from "@/components/badges";
import { Alert, Card, CardHeader, DefinitionRow, PageHeader, StatusPill } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { requireRole } from "@/lib/guards";
import { getReference, serverApiOrNull } from "@/lib/server-api";
import type { AgentPrivate } from "@/lib/types";

import { PhotoUpload, ProfileForm, VerificationUpload } from "./profile-form";

export default async function AgentProfilePage() {
  const user = await requireRole("AGENT", "LANDLORD");
  const [profile, reference] = await Promise.all([serverApiOrNull<AgentPrivate>("/api/agents/profile"), getReference()]);
  const app = profile?.latest_application ?? null;
  const canApply = profile && (!app || ["REJECTED", "EXPIRED"].includes(app.status) || profile.verification_status === "EXPIRED");

  return (
    <>
      <PageHeader
        title="Profile & verification"
        description={
          user.role === "LANDLORD"
            ? "Optional for landlords: a public profile lets renters see who they are dealing with."
            : "Complete your profile, then submit ID for the Verified Agent badge."
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <ProfileForm profile={profile} reference={reference} />
        <div className="space-y-6">
          {profile && (
            <Card className="p-5">
              <div className="flex items-center gap-4">
                <AgentAvatar name={profile.name} photo={profile.profile_photo_url} />
                <div>
                  <p className="font-semibold text-slate-900">{profile.name}</p>
                  <PhotoUpload />
                </div>
              </div>
              <div className="mt-4">
                <VerifiedAgentBadge status={profile.verification_status} expiresAt={profile.verification_expiry_date} />
              </div>
              {profile.verification_status !== "DRAFT" && (
                <Link href={`/agents/${profile.id}`} className="mt-3 block text-sm font-medium text-brand-700 hover:underline">
                  View public profile →
                </Link>
              )}
            </Card>
          )}
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
        </div>
      </div>
    </>
  );
}
