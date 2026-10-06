"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Input, Select, StatusPill } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";
import type { CheckItem, CheckResult, PropertyDocument } from "@/lib/types";

const MANDATORY = new Set([
  "AGENT_IDENTITY_SEEN",
  "AUTHORITY_TO_MARKET_SEEN",
  "PROPERTY_LOCATION_INSPECTED",
  "FEE_BREAKDOWN_CONFIRMED",
  "LISTING_AVAILABILITY_CONFIRMED",
]);

function CheckRow({
  caseId,
  check,
  documents,
  editable,
}: {
  caseId: number;
  check: CheckItem;
  documents: PropertyDocument[];
  editable: boolean;
}) {
  const router = useRouter();
  const [result, setResult] = useState<CheckResult>(check.result);
  const [note, setNote] = useState(check.evidence_note ?? "");
  const [docId, setDocId] = useState(check.document_url?.split(":")[1] ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = result !== check.result || note !== (check.evidence_note ?? "") || docId !== (check.document_url?.split(":")[1] ?? "");

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await post(`/api/verification-cases/${caseId}/checks`, {
        check_type: check.check_type,
        result,
        evidence_note: note || null,
        document_id: docId ? Number(docId) : null,
      });
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="space-y-2 px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-slate-900">
          {check.label}
          {MANDATORY.has(check.check_type) && <span className="ml-1.5 text-xs font-semibold text-amber-700">required</span>}
        </p>
        <StatusPill status={check.result} />
      </div>
      {editable ? (
        <div className="grid gap-2 sm:grid-cols-[150px_1fr_160px_auto]">
          <Select value={result} onChange={(e) => setResult(e.target.value as CheckResult)} aria-label={`${check.label} result`}>
            <option value="NOT_STARTED">Not started</option>
            <option value="PASSED">Passed</option>
            <option value="FAILED">Failed</option>
            <option value="NOT_APPLICABLE" disabled={MANDATORY.has(check.check_type)}>
              Not applicable
            </option>
          </Select>
          <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Evidence note (shown in public report)" maxLength={2000} aria-label="Evidence note" />
          <Select value={docId} onChange={(e) => setDocId(e.target.value)} aria-label="Linked document">
            <option value="">No document</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                #{d.id} {d.document_type.replace(/_/g, " ").toLowerCase()}
              </option>
            ))}
          </Select>
          <Button size="sm" onClick={save} disabled={!dirty} loading={busy}>
            Save
          </Button>
        </div>
      ) : (
        check.evidence_note && <p className="text-sm text-slate-600">{check.evidence_note}</p>
      )}
      {error && <p className="text-xs font-medium text-red-700">{error}</p>}
    </li>
  );
}

export function ChecklistEditor({
  caseId,
  checks,
  documents,
  editable,
}: {
  caseId: number;
  checks: CheckItem[];
  documents: PropertyDocument[];
  editable: boolean;
}) {
  return (
    <ul className="divide-y divide-slate-100">
      {checks.map((c) => (
        <CheckRow key={c.id} caseId={caseId} check={c} documents={documents} editable={editable} />
      ))}
    </ul>
  );
}
