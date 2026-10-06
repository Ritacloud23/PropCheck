import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { Card, EmptyState, PageHeader, StatusPill, buttonClass } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Booking } from "@/lib/types";

export default async function RenterBookings() {
  const bookings = await serverApi<Booking[]>("/api/inspection-bookings");
  return (
    <>
      <PageHeader title="Inspections" description="Never pay before you have inspected the property in person." />
      {!bookings.length ? (
        <EmptyState
          title="No inspections booked"
          action={<Link href="/properties?verified_only=true" className={buttonClass("primary", "md")}>Find a property</Link>}
        />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {bookings.map((b) => (
              <li key={b.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm">
                  <Link href={`/properties/${b.property.public_slug}`} className="font-semibold text-slate-900 hover:text-brand-700">
                    {b.property.title}
                  </Link>
                  <p className="text-slate-600">
                    {formatDateTime(b.start_time)} · {b.property.city}
                  </p>
                  {b.landlord_note && <p className="mt-1 text-slate-500">Agent note: {b.landlord_note}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <StatusPill status={b.status} />
                  {b.allowed_actions.includes("CANCELLED") && (
                    <ActionButton
                      path={`/api/inspection-bookings/${b.id}/cancel`}
                      label="Cancel"
                      variant="ghost"
                      reason={{ required: false }}
                    />
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
