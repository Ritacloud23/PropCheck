import { Card, EmptyState, Field, Input, PageHeader, Select, buttonClass } from "@/components/ui";
import { formatDateTime, humanize } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { AuditEntry } from "@/lib/types";

const ENTITY_TYPES = [
  "AgentVerification", "AgentProfile", "VerificationCase", "Property", "PropertyDocument", "InspectionSlot",
  "InspectionBooking", "HouseSearchRequest", "Reservation", "AgentReport", "User",
];

export default async function AuditLogPage(props: PageProps<"/dashboard/reviewer/audit">) {
  const sp = await props.searchParams;
  const entityType = typeof sp.entity_type === "string" && ENTITY_TYPES.includes(sp.entity_type) ? sp.entity_type : "";
  const entityId = typeof sp.entity_id === "string" && /^\d+$/.test(sp.entity_id) ? sp.entity_id : "";
  const action = typeof sp.action === "string" ? sp.action.toUpperCase().replace(/[^A-Z_]/g, "") : "";
  const q = new URLSearchParams({ limit: "200" });
  if (entityType) q.set("entity_type", entityType);
  if (entityId) q.set("entity_id", entityId);
  if (action) q.set("action", action);
  const entries = await serverApi<AuditEntry[]>(`/api/reviewer/audit-log?${q}`);

  return (
    <>
      <PageHeader title="Audit log" description="Append-only record of every approval, rejection, suspension, payment, release, refund and status change." />
      <form className="mb-5 grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-4 sm:items-end">
        <Field label="Entity" htmlFor="at">
          <Select id="at" name="entity_type" defaultValue={entityType}>
            <option value="">All</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Entity ID" htmlFor="aid">
          <Input id="aid" name="entity_id" inputMode="numeric" defaultValue={entityId} />
        </Field>
        <Field label="Action" htmlFor="aa">
          <Input id="aa" name="action" placeholder="e.g. PROPERTY_VERIFIED" defaultValue={action} />
        </Field>
        <button className={buttonClass("primary", "md")}>Filter</button>
      </form>
      {!entries.length ? (
        <EmptyState title="No matching entries" />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">When</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Entity</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Change</th>
                <th className="px-4 py-3">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((e) => (
                <tr key={e.id} className="align-top">
                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-500">{formatDateTime(e.created_at)}</td>
                  <td className="px-4 py-2.5">{e.actor_name}</td>
                  <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs">
                    {e.entity_type}#{e.entity_id}
                  </td>
                  <td className="px-4 py-2.5 font-medium">{humanize(e.action)}</td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">
                    {e.from_status || e.to_status ? `${e.from_status ?? "—"} → ${e.to_status ?? "—"}` : ""}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{e.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
