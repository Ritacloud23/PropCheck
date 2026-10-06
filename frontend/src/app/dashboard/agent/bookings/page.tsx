import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { CallButton } from "@/components/whatsapp-button";
import { formatDateTime } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Booking } from "@/lib/types";

export default async function AgentBookings() {
  const bookings = await serverApi<Booking[]>("/api/inspection-bookings");
  return (
    <>
      <PageHeader title="Inspection requests" description="Confirm or decline quickly — renters see the status in real time." />
      {!bookings.length ? (
        <EmptyState title="No inspection requests yet">Add inspection slots to your listings so renters can book.</EmptyState>
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => (
            <Card key={b.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="text-sm">
                  <Link href={`/dashboard/agent/properties/${b.property.id}`} className="font-semibold text-slate-900 hover:text-brand-700">
                    {b.property.title}
                  </Link>
                  <p className="text-slate-600">{formatDateTime(b.start_time)}</p>
                  <p className="mt-1 text-slate-700">
                    {b.renter_name} {b.renter_note && <span className="text-slate-500">— “{b.renter_note}”</span>}
                  </p>
                </div>
                <StatusPill status={b.status} />
              </div>
              <div className="mt-3 flex flex-wrap items-start gap-2">
                {b.renter_phone && ["REQUESTED", "CONFIRMED"].includes(b.status) && <CallButton number={b.renter_phone} className="h-9 text-sm" />}
                {b.allowed_actions.includes("CONFIRMED") && (
                  <ActionButton path={`/api/inspection-bookings/${b.id}/confirm`} label="Confirm" variant="primary" />
                )}
                {b.allowed_actions.includes("DECLINED") && (
                  <ActionButton
                    path={`/api/inspection-bookings/${b.id}/decline`}
                    label="Decline"
                    variant="secondary"
                    reason={{ required: true, label: "Reason shown to the renter" }}
                  />
                )}
                {b.allowed_actions.includes("COMPLETED") && (
                  <ActionButton path={`/api/inspection-bookings/${b.id}/complete`} label="Mark inspected" />
                )}
                {b.allowed_actions.includes("CANCELLED") && (
                  <ActionButton path={`/api/inspection-bookings/${b.id}/cancel`} label="Cancel" variant="ghost" reason={{ required: false }} />
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
