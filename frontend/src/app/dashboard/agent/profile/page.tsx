import Link from "next/link";

import { AgentAvatar } from "@/components/agent-card";
import { VerifiedAgentBadge } from "@/components/badges";
import { Card, PageHeader } from "@/components/ui";
import { requireRole } from "@/lib/guards";
import { getReference, serverApiOrNull } from "@/lib/server-api";
import type { AgentPrivate } from "@/lib/types";

import { AgentVerificationCard } from "../verification/agent-verification-card";
import { PhotoUpload, ProfileForm } from "./profile-form";

export default async function AgentProfilePage() {
  const user = await requireRole("AGENT", "LANDLORD");
  const [profile, reference] = await Promise.all([serverApiOrNull<AgentPrivate>("/api/agents/profile"), getReference()]);

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
          <AgentVerificationCard profile={profile} />
        </div>
      </div>
    </>
  );
}
