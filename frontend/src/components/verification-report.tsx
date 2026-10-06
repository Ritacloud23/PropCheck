import { CheckCircle2, CircleDashed, MinusCircle, XCircle } from "lucide-react";

import { formatDate, humanize } from "@/lib/format";
import type { CheckResult, VerificationReport as Report } from "@/lib/types";

import { VerifiedPropertyBadge } from "./badges";
import { Disclaimer, SafetyWarning } from "./disclaimer";
import { DefinitionRow, StatusPill } from "./ui";

const RESULT_ICON: Record<CheckResult, { icon: typeof CheckCircle2; cls: string; label: string }> = {
  PASSED: { icon: CheckCircle2, cls: "text-green-600", label: "Passed" },
  FAILED: { icon: XCircle, cls: "text-red-600", label: "Failed" },
  NOT_APPLICABLE: { icon: MinusCircle, cls: "text-slate-400", label: "Not applicable" },
  NOT_STARTED: { icon: CircleDashed, cls: "text-slate-400", label: "Not checked" },
};

export function VerificationReport({ report }: { report: Report }) {
  const neverSubmitted = report.status === "NOT_SUBMITTED";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <VerifiedPropertyBadge status={report.status} expiresAt={report.expires_at} />
        {report.verification_reference && (
          <span className="font-mono text-sm text-slate-600">Ref: {report.verification_reference}</span>
        )}
      </div>

      {neverSubmitted ? (
        <p className="text-sm text-slate-600">
          This listing has not been submitted for verification. PropCheck has not checked the agent&apos;s authority,
          the location, photos or fees. Treat it with extra care.
        </p>
      ) : (
        <>
          {report.status === "REJECTED" && report.rejection_reason && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
              <p className="font-semibold">Verification failed</p>
              <p className="mt-1">{report.rejection_reason}</p>
            </div>
          )}
          {report.status === "EXPIRED" && (
            <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-900">
              This verification has expired or the listing changed after it was checked. The results below may no
              longer be accurate.
            </div>
          )}

          <dl className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white px-4">
            <DefinitionRow label="Submitted">{formatDate(report.submitted_at)}</DefinitionRow>
            <DefinitionRow label="Inspection date">{formatDate(report.inspection_date)}</DefinitionRow>
            <DefinitionRow label="Verified on">{formatDate(report.verified_at)}</DefinitionRow>
            <DefinitionRow label="Valid until">{formatDate(report.expires_at)}</DefinitionRow>
            <DefinitionRow label="Reviewer reference">{report.reviewer_reference ?? "—"}</DefinitionRow>
          </dl>

          <section>
            <h3 className="mb-3 font-semibold text-slate-900">Checklist</h3>
            <ul className="space-y-2">
              {report.checks.map((c) => {
                const r = RESULT_ICON[c.result];
                return (
                  <li key={c.check_type} className="flex gap-3 rounded-lg bg-white p-3 ring-1 ring-slate-200">
                    <r.icon className={`mt-0.5 size-5 shrink-0 ${r.cls}`} aria-label={r.label} />
                    <div className="min-w-0 text-sm">
                      <p className="font-medium text-slate-900">
                        {c.label} <span className="font-normal text-slate-500">· {r.label}</span>
                      </p>
                      {c.evidence_note && <p className="text-slate-600">{c.evidence_note}</p>}
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          {report.documents_reviewed.length > 0 && (
            <section>
              <h3 className="mb-3 font-semibold text-slate-900">Supporting documents</h3>
              <p className="mb-2 text-xs text-slate-500">
                Documents are private. Only those marked Accepted or Reviewed were examined by PropCheck; Uploaded means
                not yet reviewed.
              </p>
              <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
                {report.documents_reviewed.map((d, i) => (
                  <li key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <span>{humanize(d.document_type)}</span>
                    <StatusPill status={d.review_status} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-green-200 bg-green-50/60 p-4">
          <h3 className="mb-2 font-semibold text-green-900">What was checked</h3>
          {report.what_was_checked.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-green-900">
              {report.what_was_checked.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-green-900">Nothing has been confirmed yet.</p>
          )}
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 font-semibold text-slate-900">What was NOT checked</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {report.what_was_not_checked.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
      </div>

      <section>
        <h3 className="mb-2 font-semibold text-slate-900">Limitations</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
          {report.limitations.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <p className="mt-2 text-sm text-slate-600">{report.agent_note}</p>
      </section>

      {report.timeline.length > 0 && (
        <section>
          <h3 className="mb-2 font-semibold text-slate-900">Verification history</h3>
          <ol className="space-y-1 text-sm text-slate-600">
            {report.timeline.map((t, i) => (
              <li key={i}>
                <span className="text-slate-400">{formatDate(t.at)}</span> · {humanize(t.action)}
              </li>
            ))}
          </ol>
        </section>
      )}

      <SafetyWarning />
      <Disclaimer />
    </div>
  );
}
