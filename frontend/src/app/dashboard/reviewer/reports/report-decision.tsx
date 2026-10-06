"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Checkbox, Textarea } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";

export function ReportDecision({ reportId, canSuspend }: { reportId: number; canSuspend: boolean }) {
  const router = useRouter();
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [suspend, setSuspend] = useState(false);
  const [busy, setBusy] = useState<"resolve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (decision: "resolve" | "reject") => {
    if (reason.trim().length < 3) {
      setError("A reason is required (it is shown to the reporter).");
      return;
    }
    if (decision === "resolve" && suspend && !window.confirm("Resolve this report AND suspend the agent?")) return;
    setBusy(decision);
    setError(null);
    try {
      await post(`/api/reviewer/reports/${reportId}/${decision}`, {
        reason: reason.trim(),
        reviewer_notes: notes.trim() || null,
        suspend_agent: decision === "resolve" && suspend,
      });
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-4">
      <label className="block text-xs font-medium text-slate-700">
        Decision reason (shown to the reporter)
        <Textarea value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 min-h-16" maxLength={1000} />
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Internal notes (optional)
        <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="mt-1 min-h-12" maxLength={4000} />
      </label>
      {canSuspend && (
        <Checkbox checked={suspend} onChange={(e) => setSuspend(e.target.checked)} label="Also suspend this agent (only when resolving)" />
      )}
      {error && <p className="text-xs font-medium text-red-700">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={suspend ? "danger" : "primary"} loading={busy === "resolve"} onClick={() => decide("resolve")}>
          {suspend ? "Resolve & suspend agent" : "Resolve (upheld)"}
        </Button>
        <Button size="sm" variant="secondary" loading={busy === "reject"} onClick={() => decide("reject")}>
          Reject report
        </Button>
      </div>
    </div>
  );
}
