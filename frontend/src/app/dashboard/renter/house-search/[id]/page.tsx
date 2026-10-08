import Link from "next/link";
import { notFound } from "next/navigation";

import { Alert, Card, CardHeader, DefinitionRow, PageHeader } from "@/components/ui";
import { formatDate, formatNgPhone, humanize } from "@/lib/format";
import { serverApiOrNull } from "@/lib/server-api";
import type { HouseSearchRequest } from "@/lib/types";

import { RequestCard } from "../request-card";

export default async function RenterRequestDetail(props: PageProps<"/dashboard/renter/house-search/[id]">) {
  const { id } = await props.params;
  if (!/^\d+$/.test(id)) notFound();
  // The API returns 404 for requests that belong to someone else.
  const r = await serverApiOrNull<HouseSearchRequest>(`/api/house-search-requests/${id}`);
  if (!r) notFound();

  return (
    <>
      <Link href="/dashboard/renter/house-search" className="text-sm font-medium text-brand-700 hover:underline">
        ← All requests
      </Link>
      <PageHeader title={`Request #${r.id}`} description="Only you, PropCheck reviewers and the agent assigned to you can see this request." />
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <RequestCard request={r} />
          <Alert tone="warning">Do not send money before confirming the property, agent authority and payment terms.</Alert>
        </div>
        <Card>
          <CardHeader title="What you asked for" />
          <dl className="divide-y divide-slate-100 px-5 pb-3">
            <DefinitionRow label="Status">{humanize(r.status)}</DefinitionRow>
            <DefinitionRow label="Local government area">{r.local_government_area ?? "—"}</DefinitionRow>
            <DefinitionRow label="Move-in date">{r.preferred_move_in_date ? formatDate(r.preferred_move_in_date) : "Flexible"}</DefinitionRow>
            <DefinitionRow label="Furnishing">{humanize(r.furnished_preference)}</DefinitionRow>
            <DefinitionRow label="Phone">{formatNgPhone(r.phone)}</DefinitionRow>
            <DefinitionRow label="WhatsApp">{r.whatsapp_number ? formatNgPhone(r.whatsapp_number) : "—"}</DefinitionRow>
            <DefinitionRow label="Email">{r.email ?? "—"}</DefinitionRow>
            <DefinitionRow label="Share with agents">{r.consent_to_share ? "Yes, with the assigned agent" : "No"}</DefinitionRow>
            <DefinitionRow label="Last updated">{formatDate(r.updated_at)}</DefinitionRow>
          </dl>
          {r.description && <p className="border-t border-slate-100 px-5 py-4 text-sm text-slate-700">{r.description}</p>}
        </Card>
      </div>
    </>
  );
}
