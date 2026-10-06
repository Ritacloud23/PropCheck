import Link from "next/link";
import { Suspense } from "react";

import { ActionButton } from "@/components/action-button";
import { Alert, Card, DefinitionRow, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDateTime, formatNaira } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Reservation } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ConfirmKeysButton, PayButton, PaystackReturn } from "./reservation-actions";

const STATUS_HELP: Record<string, string> = {
  PENDING_PAYMENT: "Not paid yet. You can cancel at no cost.",
  PENDING_RELEASE: "Paid (test). Held until you confirm you have the keys, or a reviewer approves a refund.",
  RELEASED: "You confirmed the keys. The reservation was released.",
  REFUNDED: "Refunded (test mode).",
  CANCELLED: "Cancelled before payment.",
};

export default async function RenterReservations(props: PageProps<"/dashboard/renter/reservations">) {
  const { highlight } = await props.searchParams;
  const reservations = await serverApi<Reservation[]>("/api/reservations");
  return (
    <>
      <PageHeader title="Reservations" />
      <Alert tone="warning" title="Test / demo only" className="mb-6">
        No real money is collected. PropCheck is not an escrow service and this workflow is not legally protected escrow.
      </Alert>
      <Suspense>
        <PaystackReturn reservations={reservations} />
      </Suspense>
      {!reservations.length ? (
        <EmptyState title="No reservations">Verified, available listings show a “Reserve (test mode)” option.</EmptyState>
      ) : (
        <div className="space-y-4">
          {reservations.map((r) => (
            <Card key={r.id} className={cn("p-5", String(r.id) === highlight && "ring-2 ring-brand-600")}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link href={`/properties/${r.property.public_slug}`} className="font-semibold text-slate-900 hover:text-brand-700">
                    {r.property.title}
                  </Link>
                  <p className="text-sm text-slate-600">{STATUS_HELP[r.status]}</p>
                </div>
                <StatusPill status={r.status} />
              </div>
              <dl className="mt-3 grid divide-y divide-slate-100 sm:max-w-md">
                <DefinitionRow label="Amount">{formatNaira(r.amount)}</DefinitionRow>
                <DefinitionRow label="Payment reference">{r.payment_reference ?? "—"}</DefinitionRow>
                <DefinitionRow label="Created">{formatDateTime(r.created_at)}</DefinitionRow>
                {r.paid_at && <DefinitionRow label="Paid">{formatDateTime(r.paid_at)}</DefinitionRow>}
                {r.released_at && <DefinitionRow label="Released">{formatDateTime(r.released_at)}</DefinitionRow>}
                {r.refunded_at && <DefinitionRow label="Refunded">{formatDateTime(r.refunded_at)}</DefinitionRow>}
              </dl>
              {r.refund_requested_at && r.status === "PENDING_RELEASE" && (
                <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Refund requested {formatDateTime(r.refund_requested_at)} — waiting for a reviewer.
                </p>
              )}
              <div className="mt-4 flex flex-wrap items-start gap-2">
                {r.allowed_actions.includes("PENDING_RELEASE") && <PayButton reservation={r} />}
                {r.allowed_actions.includes("RELEASED") && <ConfirmKeysButton id={r.id} />}
                {r.status === "PENDING_RELEASE" && !r.refund_requested_at && (
                  <ActionButton
                    path={`/api/reservations/${r.id}/request-refund`}
                    label="Request refund"
                    reason={{ required: true, label: "What went wrong?" }}
                  />
                )}
                {r.allowed_actions.includes("CANCELLED") && (
                  <ActionButton path={`/api/reservations/${r.id}/cancel`} label="Cancel" variant="ghost" reason={{ required: false }} />
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
