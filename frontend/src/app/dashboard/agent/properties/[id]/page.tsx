import { CheckCircle2, Circle } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ActionButton } from "@/components/action-button";
import { VerifiedPropertyBadge } from "@/components/badges";
import { Alert, Card, CardHeader, DefinitionRow, EmptyState, PageHeader, StatusPill } from "@/components/ui";
import { formatDate, formatDateTime, humanize } from "@/lib/format";
import { localMedia } from "@/lib/media";
import { getReference, serverApi, serverApiOrNull } from "@/lib/server-api";
import type { PropertyDetail, Slot, VerificationCase } from "@/lib/types";

import { PropertyForm } from "../property-form";
import { DocumentUpload, ListingControls, MediaUpload, SlotCreator } from "./manage-client";

const OPEN_CASE = ["DRAFT", "SUBMITTED", "IN_REVIEW", "INSPECTION_BOOKED"];

export default async function ManagePropertyPage(props: PageProps<"/dashboard/agent/properties/[id]">) {
  const { id } = await props.params;
  if (!/^\d+$/.test(id)) notFound();
  const property = await serverApiOrNull<PropertyDetail>(`/api/properties/${id}`);
  if (!property || !property.can_manage) notFound();
  const [reference, slots, verificationCase] = await Promise.all([
    getReference(),
    serverApi<Slot[]>(`/api/properties/${id}/slots`),
    property.latest_case_id ? serverApiOrNull<VerificationCase>(`/api/verification-cases/${property.latest_case_id}`) : null,
  ]);
  const docs = property.documents ?? [];
  const caseOpen = verificationCase && OPEN_CASE.includes(verificationCase.status);
  const canOpenCase = !caseOpen && !property.verification.is_currently_verified;
  const upcomingSlots = slots.filter((s) => s.status !== "CANCELLED" && new Date(s.end_time) > new Date());

  return (
    <>
      <PageHeader
        title={property.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <VerifiedPropertyBadge status={property.verification.status} expiresAt={property.verification.expires_at} />
            <Link href={`/properties/${property.public_slug}`} className="text-sm font-medium text-brand-700 hover:underline">
              View public listing →
            </Link>
          </span>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader title="Property verification" description="Independent of your agent badge. Reviewed by a PropCheck reviewer." />
            <div className="space-y-4 p-5">
              {verificationCase && (
                <dl className="divide-y divide-slate-100">
                  <DefinitionRow label="Reference">{verificationCase.verification_reference}</DefinitionRow>
                  <DefinitionRow label="Status">
                    <StatusPill status={verificationCase.effective_status} />
                  </DefinitionRow>
                  {verificationCase.submitted_at && <DefinitionRow label="Submitted">{formatDate(verificationCase.submitted_at)}</DefinitionRow>}
                  {verificationCase.inspection_scheduled_for && (
                    <DefinitionRow label="Reviewer inspection">{formatDateTime(verificationCase.inspection_scheduled_for)}</DefinitionRow>
                  )}
                  {verificationCase.expires_at && <DefinitionRow label="Valid until">{formatDate(verificationCase.expires_at)}</DefinitionRow>}
                </dl>
              )}
              {verificationCase?.status === "REJECTED" && verificationCase.rejection_reason && (
                <Alert tone="danger" title="Verification was not approved">
                  {verificationCase.rejection_reason}
                </Alert>
              )}
              {verificationCase?.status === "DRAFT" && (
                <>
                  <ul className="space-y-1.5 text-sm">
                    {[
                      [property.media.length > 0, "At least one photo"],
                      [docs.length > 0, "At least one supporting document (e.g. authority letter from the owner)"],
                    ].map(([ok, label]) => (
                      <li key={String(label)} className="flex items-center gap-2">
                        {ok ? <CheckCircle2 className="size-4 text-green-600" /> : <Circle className="size-4 text-slate-300" />}
                        {label}
                      </li>
                    ))}
                  </ul>
                  <ActionButton path={`/api/verification-cases/${verificationCase.id}/submit`} label="Submit for review" variant="primary" size="md" />
                </>
              )}
              {verificationCase && ["SUBMITTED", "IN_REVIEW", "INSPECTION_BOOKED"].includes(verificationCase.status) && (
                <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
                  {verificationCase.checks.map((c) => (
                    <li key={c.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                      <span>{c.label}</span>
                      <StatusPill status={c.result} />
                    </li>
                  ))}
                </ul>
              )}
              {canOpenCase && (
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">
                    {verificationCase ? "Start a new verification case for this listing." : "This listing has not been submitted for verification yet."}
                  </p>
                  <ActionButton path={`/api/properties/${property.id}/verification`} label="Start verification" variant="primary" size="md" />
                </div>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Photos" description="Public. Reviewers compare these with what they see at inspection." />
            <div className="space-y-4 p-5">
              {property.media.length > 0 && (
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                  {property.media.map((m) => (
                    // eslint-disable-next-line @next/next/no-img-element -- media is served by the API / Cloudinary
                    <img key={m.id} src={localMedia(m.url)!} alt={m.caption ?? ""} className="aspect-square w-full rounded-lg object-cover" />
                  ))}
                </div>
              )}
              <MediaUpload propertyId={property.id} disabled={property.media.length >= 15} />
            </div>
          </Card>

          <Card>
            <CardHeader title="Supporting documents" description="Private — only you and PropCheck reviewers can open them." />
            <div className="space-y-4 p-5">
              {docs.length > 0 && (
                <ul className="divide-y divide-slate-100 rounded-xl ring-1 ring-slate-200">
                  {docs.map((d) => (
                    <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                      <span>
                        <span className="font-medium">{humanize(d.document_type)}</span>
                        <span className="block text-xs text-slate-500">
                          {d.original_filename} · {formatDate(d.uploaded_at)}
                        </span>
                        {d.reviewer_notes && <span className="block text-xs text-slate-600">Reviewer: {d.reviewer_notes}</span>}
                      </span>
                      <span className="flex items-center gap-3">
                        <StatusPill status={d.review_status} />
                        {d.link && (
                          <a href={d.link} target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                            Open
                          </a>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <DocumentUpload propertyId={property.id} documentTypes={reference.document_types} />
            </div>
          </Card>

          <PropertyForm property={property} reference={reference} />
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Listing status" />
            <div className="p-5">
              <ListingControls propertyId={property.id} availability={property.availability_status} isListed={property.is_listed} />
            </div>
          </Card>
          <Card>
            <CardHeader title="Inspection slots" description="Renters book these from the listing page." />
            <div className="space-y-4 p-5">
              {upcomingSlots.length ? (
                <ul className="space-y-2">
                  {upcomingSlots.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                      <span>{formatDateTime(s.start_time)}</span>
                      <span className="flex items-center gap-2">
                        <StatusPill status={s.status} />
                        {s.status === "OPEN" && (
                          <ActionButton path={`/api/inspection-slots/${s.id}/cancel`} label="Remove" variant="ghost" />
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No upcoming slots" />
              )}
              <SlotCreator propertyId={property.id} />
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
