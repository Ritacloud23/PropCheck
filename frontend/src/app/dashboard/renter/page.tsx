import Link from "next/link";

import { SafetyWarning } from "@/components/disclaimer";
import { Card, CardHeader, EmptyState, PageHeader, StatusPill, buttonClass } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { requireRole } from "@/lib/guards";
import { serverApi } from "@/lib/server-api";
import type { Booking, HouseSearchRequest, Reservation } from "@/lib/types";

export default async function RenterHome() {
  const user = await requireRole("RENTER");
  const [requests, bookings, reservations] = await Promise.all([
    serverApi<HouseSearchRequest[]>("/api/house-search-requests"),
    serverApi<Booking[]>("/api/inspection-bookings"),
    serverApi<Reservation[]>("/api/reservations"),
  ]);
  const upcoming = bookings.filter((b) => ["REQUESTED", "CONFIRMED"].includes(b.status));
  const stats = [
    { label: "Open requests", value: requests.filter((r) => !["COMPLETED", "CANCELLED"].includes(r.status)).length, href: "/dashboard/renter/requests" },
    { label: "Upcoming inspections", value: upcoming.length, href: "/dashboard/renter/bookings" },
    { label: "Active reservations", value: reservations.filter((r) => r.status.startsWith("PENDING")).length, href: "/dashboard/renter/reservations" },
  ];

  return (
    <>
      <PageHeader
        title={`Hello, ${user.full_name.split(" ")[0]}`}
        action={
          <div className="flex gap-2">
            <Link href="/properties?verified_only=true" className={buttonClass("secondary", "md")}>
              Browse verified homes
            </Link>
            <Link href="/find-an-agent" className={buttonClass("primary", "md")}>
              Request an agent
            </Link>
          </div>
        }
      />
      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <Link key={s.label} href={s.href} className="rounded-xl bg-white p-5 ring-1 ring-slate-200 hover:ring-brand-600">
            <p className="text-3xl font-bold text-slate-900">{s.value}</p>
            <p className="text-sm text-slate-600">{s.label}</p>
          </Link>
        ))}
      </div>
      <Card className="mt-6">
        <CardHeader title="Upcoming inspections" />
        {upcoming.length ? (
          <ul className="divide-y divide-slate-100">
            {upcoming.map((b) => (
              <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                <span>
                  <Link href={`/properties/${b.property.public_slug}`} className="font-medium text-slate-900 hover:text-brand-700">
                    {b.property.title}
                  </Link>
                  <span className="block text-slate-500">{formatDateTime(b.start_time)}</span>
                </span>
                <StatusPill status={b.status} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-5">
            <EmptyState title="No inspections booked">Open a listing and choose an inspection time.</EmptyState>
          </div>
        )}
      </Card>
      <SafetyWarning className="mt-6" />
    </>
  );
}
