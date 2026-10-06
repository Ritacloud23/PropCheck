import Link from "next/link";

import { VerifiedAgentBadge } from "@/components/badges";
import { Alert, PageHeader, buttonClass } from "@/components/ui";
import { requireRole } from "@/lib/guards";
import { serverApi, serverApiOrNull } from "@/lib/server-api";
import type { AgentEnquiry, AgentPrivate, Booking, PropertyCard } from "@/lib/types";

export default async function AgentHome() {
  const user = await requireRole("AGENT", "LANDLORD");
  const [profile, properties, bookings, enquiries] = await Promise.all([
    serverApiOrNull<AgentPrivate>("/api/agents/profile"),
    serverApi<PropertyCard[]>("/api/properties/mine"),
    serverApi<Booking[]>("/api/inspection-bookings?status=REQUESTED"),
    user.role === "AGENT" ? serverApi<AgentEnquiry[]>("/api/agent/enquiries") : Promise.resolve([]),
  ]);
  const verified = properties.filter((p) => p.verification.is_currently_verified).length;
  const stats = [
    { label: "Listings", value: properties.length, href: "/dashboard/agent/properties" },
    { label: "Verified listings", value: verified, href: "/dashboard/agent/properties" },
    { label: "Inspection requests to answer", value: bookings.length, href: "/dashboard/agent/bookings" },
    ...(user.role === "AGENT"
      ? [{ label: "Matched renters waiting", value: enquiries.filter((e) => e.status === "PENDING").length, href: "/dashboard/agent/enquiries" }]
      : []),
  ];

  return (
    <>
      <PageHeader
        title={`Welcome, ${user.full_name.split(" ")[0]}`}
        action={
          <Link href="/dashboard/agent/properties/new" className={buttonClass("primary", "md")}>
            Add a listing
          </Link>
        }
      />
      {user.role === "AGENT" && !profile && (
        <Alert tone="warning" title="Finish setting up" className="mb-6">
          Create your agent profile before listing properties.{" "}
          <Link href="/dashboard/agent/profile" className="font-semibold underline">
            Create profile
          </Link>
        </Alert>
      )}
      {profile && (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200">
          <span className="text-sm text-slate-600">Your agent status:</span>
          <VerifiedAgentBadge status={profile.verification_status} expiresAt={profile.verification_expiry_date} />
          {profile.verification_status === "DRAFT" && (
            <Link href="/dashboard/agent/profile" className="text-sm font-semibold text-brand-700 hover:underline">
              Submit ID for verification →
            </Link>
          )}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s) => (
          <Link key={s.label} href={s.href} className="rounded-xl bg-white p-5 ring-1 ring-slate-200 hover:ring-brand-600">
            <p className="text-3xl font-bold text-slate-900">{s.value}</p>
            <p className="text-sm text-slate-600">{s.label}</p>
          </Link>
        ))}
      </div>
      <Alert tone="info" className="mt-6">
        Your agent badge and each listing&apos;s verification are separate. Renters see “Not yet verified” on any listing you
        haven&apos;t submitted for review.
      </Alert>
    </>
  );
}
