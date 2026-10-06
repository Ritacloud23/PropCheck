import { ActionButton } from "@/components/action-button";
import { StatusTabs } from "@/components/status-tabs";
import { Alert, Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDateTime, formatNaira } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Reservation } from "@/lib/types";

const TABS = ["PENDING_RELEASE", "RELEASED", "REFUNDED", "PENDING_PAYMENT", "CANCELLED"];

export default async function ReviewerReservations(props: PageProps<"/dashboard/reviewer/reservations">) {
  const { status } = await props.searchParams;
  const current = typeof status === "string" && TABS.includes(status) ? status : "PENDING_RELEASE";
  const reservations = await serverApi<Reservation[]>(`/api/reservations?status=${current}`);
  const sorted = [...reservations].sort((a, b) => Number(!!b.refund_requested_at) - Number(!!a.refund_requested_at));
  return (
    <>
      <PageHeader title="Reservations & refunds" />
      <Alert tone="warning" className="mb-5">
        Test mode only. A refund moves a PENDING_RELEASE reservation to REFUNDED once; released reservations cannot be refunded.
      </Alert>
      <StatusTabs basePath="/dashboard/reviewer/reservations" options={TABS} current={current} />
      {!sorted.length ? (
        <EmptyState title="Nothing here" />
      ) : (
        <div className="space-y-3">
          {sorted.map((r) => (
            <Card key={r.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3 text-sm">
                <div>
                  <p className="font-semibold text-slate-900">{r.property.title}</p>
                  <p className="text-slate-600">
                    {r.renter_name} · {formatNaira(r.amount)} · ref {r.payment_reference ?? "—"} · paid {formatDateTime(r.paid_at)}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </div>
              {r.refund_requested_at && (
                <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Refund requested {formatDateTime(r.refund_requested_at)}: “{r.refund_request_reason}”
                </p>
              )}
              {r.allowed_actions.includes("REFUNDED") && (
                <div className="mt-3">
                  <ActionButton
                    path={`/api/reservations/${r.id}/refund`}
                    label="Refund (test)"
                    variant="danger"
                    reason={{ required: true, label: "Decision reason (audited)" }}
                  />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
