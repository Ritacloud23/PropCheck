import { redirect } from "next/navigation";

import { DashboardNav, type NavItem } from "@/components/dashboard-nav";
import { SiteHeader } from "@/components/site-header";
import { humanize } from "@/lib/format";
import { getCurrentUser } from "@/lib/server-api";
import type { Role } from "@/lib/types";

const NAV: Record<Role, NavItem[]> = {
  RENTER: [
    { href: "/dashboard/renter", label: "Overview" },
    { href: "/dashboard/renter/house-search", label: "House-search requests" },
    { href: "/dashboard/renter/bookings", label: "Inspections" },
    { href: "/dashboard/renter/reservations", label: "Reservations" },
    { href: "/dashboard/renter/reports", label: "My reports" },
  ],
  AGENT: [
    { href: "/dashboard/agent", label: "Overview" },
    { href: "/dashboard/agent/profile", label: "Profile" },
    { href: "/dashboard/agent/verification", label: "Verification" },
    { href: "/dashboard/agent/properties", label: "My listings" },
    { href: "/dashboard/agent/inspection-slots", label: "Inspections" },
    { href: "/dashboard/agent/enquiries", label: "Matched renters" },
    { href: "/dashboard/agent/reservations", label: "Reservations" },
  ],
  LANDLORD: [
    { href: "/dashboard/agent", label: "Overview" },
    { href: "/dashboard/agent/properties", label: "My properties" },
    { href: "/dashboard/agent/verification", label: "Verification" },
    { href: "/dashboard/agent/inspection-slots", label: "Inspections" },
    { href: "/dashboard/agent/reservations", label: "Reservations" },
    { href: "/dashboard/agent/profile", label: "Public profile (optional)" },
  ],
  REVIEWER: [
    { href: "/dashboard/reviewer", label: "Overview" },
    { href: "/dashboard/reviewer/agents", label: "Agent applications" },
    { href: "/dashboard/reviewer/cases", label: "Property cases" },
    { href: "/dashboard/reviewer/requests", label: "House-search matching" },
    { href: "/dashboard/reviewer/reports", label: "Reports" },
    { href: "/dashboard/reviewer/place-reports", label: "Nearby place reports" },
    { href: "/dashboard/reviewer/reservations", label: "Refunds" },
    { href: "/dashboard/reviewer/audit-log", label: "Audit log" },
  ],
  ADMIN: [],
};
NAV.ADMIN = NAV.REVIEWER;

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/dashboard");
  return (
    <>
      <SiteHeader />
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[220px_1fr] lg:py-8">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <p className="mb-3 hidden text-xs font-semibold uppercase tracking-wide text-slate-500 lg:block">
            {humanize(user.role)} dashboard
          </p>
          <DashboardNav items={NAV[user.role]} />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </>
  );
}
