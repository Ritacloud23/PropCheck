import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { Card, CardHeader, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { CallButton } from "@/components/whatsapp-button";
import { formatDateTime } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Booking, PropertyCard, Slot } from "@/lib/types";

export default async function AgentInspections() {
  const [bookings, properties] = await Promise.all([
    serverApi<Booking[]>("/api/inspection-bookings"),
    serverApi<PropertyCard[]>("/api/properties/mine"),
  ]);
  const slotsByProperty = await Promise.all(
    properties.map(async (p) => ({
      property: p,
      slots: (await serverApi<Slot[]>(`/api/properties/${p.id}/inspection-slots`)).filter(
        (s) => s.status !== "CANCELLED" && new Date(s.end_time) > new Date(),
      ),
    })),
  );
  return (
    <>
      <PageHeader
        title="Inspection slots & requests"
        description="Publish slots on each listing, then confirm or decline requests quickly — renters see the status straight away."
      />
      <Card className="mb-6">
        <CardHeader title="Upcoming slots" description="Slots for the same listing cannot overlap, and each slot takes one booking." />
        {!properties.length ? (
          <p className="p-5 text-sm text-slate-600">
            <Link href="/dashboard/agent/properties/new" className="font-semibold text-brand-700 hover:underline">Add a listing</Link> first.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {slotsByProperty.map(({ property, slots }) => (
              <li key={property.id} className="flex flex-wrap items-start justify-between gap-3 p-5 text-sm">
                <div>
                  <p className="font-semibold text-slate-900">{property.title}</p>
                  {slots.length ? (
                    <ul className="mt-1 space-y-0.5 text-slate-600">
                      {slots.map((s) => (
                        <li key={s.id}>
                          {formatDateTime(s.start_time)} · <span className={s.status === "BOOKED" ? "font-medium text-amber-700" : ""}>{s.status === "BOOKED" ? "Booked" : "Open"}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-slate-500">No upcoming slots.</p>
                  )}
                </div>
                <Link href={`/dashboard/agent/properties/${property.id}`} className="font-medium text-brand-700 hover:underline">
                  Add or cancel slots →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <h2 className="mb-3 text-lg font-semibold text-slate-900">Inspection requests</h2>
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
