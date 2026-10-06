import type { Metadata } from "next";
import Link from "next/link";

import { SafetyWarning } from "@/components/disclaimer";
import { Alert, Card, PageHeader, buttonClass } from "@/components/ui";
import { getCurrentUser, getReference, serverApiOrNull } from "@/lib/server-api";
import type { AgentPublic } from "@/lib/types";

import { HouseSearchForm } from "./house-search-form";

export const metadata: Metadata = {
  title: "Help me find a house",
  description: "Tell PropCheck what you need and we'll match you with a verified agent who covers your area.",
};

export default async function FindAnAgentPage(props: PageProps<"/find-an-agent">) {
  const { agent: agentParam } = await props.searchParams;
  const [user, reference] = await Promise.all([getCurrentUser(), getReference()]);
  const preferred =
    typeof agentParam === "string" && /^\d+$/.test(agentParam)
      ? await serverApiOrNull<AgentPublic>(`/api/agents/${agentParam}`)
      : null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <PageHeader
        title="I need help finding a house"
        description="Tell us what you're looking for. A PropCheck reviewer matches you with one verified agent who covers your area — your details are shared only with that agent."
      />
      {preferred && (
        <Alert tone="info" className="mb-4">
          You came from <strong>{preferred.name}</strong>&apos;s profile. Mention them in the notes and we&apos;ll try to
          match you with them if they cover your area.
        </Alert>
      )}
      {!user ? (
        <Card className="p-6 text-center">
          <p className="font-semibold text-slate-900">Log in or create a free renter account to send a request.</p>
          <p className="mt-1 text-sm text-slate-600">We need an account so you can track replies and stay in control of your data.</p>
          <div className="mt-5 flex justify-center gap-2">
            <Link href="/login?next=/find-an-agent" className={buttonClass("secondary", "md")}>
              Log in
            </Link>
            <Link href="/register?role=RENTER" className={buttonClass("primary", "md")}>
              Create account
            </Link>
          </div>
        </Card>
      ) : user.role !== "RENTER" ? (
        <Alert tone="warning">House-search requests are for renter accounts. You are logged in as {user.role.toLowerCase()}.</Alert>
      ) : (
        <HouseSearchForm reference={reference} user={user} />
      )}
      <SafetyWarning className="mt-6" />
    </div>
  );
}
