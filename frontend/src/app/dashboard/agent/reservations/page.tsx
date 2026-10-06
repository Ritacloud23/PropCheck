import { Alert, Card, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDateTime, formatNaira } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Reservation } from "@/lib/types";

export default async function AgentReservations() {
  const reservations = await serverApi<Reservation[]>("/api/reservations");
  return (
    <>
      <PageHeader title="Reservations" description="Test-mode reservations renters made on your listings." />
      <Alert tone="warning" className="mb-6">
        Demo only: no money is collected or paid out. Hand over keys only after you have received payment through your normal,
        agreed channel.
      </Alert>
      {!reservations.length ? (
        <EmptyState title="No reservations on your listings" />
      ) : (
        <Card>
          <ul className="divide-y divide-slate-100">
            {reservations.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 text-sm">
                <div>
                  <p className="font-semibold text-slate-900">{r.property.title}</p>
                  <p className="text-slate-600">
                    {r.renter_name} · {formatNaira(r.amount)} · {formatDateTime(r.created_at)}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
