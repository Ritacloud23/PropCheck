"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert, Button, Card, Field, Input, Select, Textarea } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { Report } from "@/lib/types";

export function ReportForm({
  target,
  reasons,
}: {
  target: { kind: "agent" | "property"; id: number; name: string };
  reasons: string[];
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<Report | null>(null);

  if (done) {
    return (
      <Alert tone="success" title="Thank you — your report was received">
        A PropCheck reviewer will look into it. You can follow its status in{" "}
        <Link href="/dashboard/renter/reports" className="font-semibold underline">
          your dashboard
        </Link>
        .
      </Alert>
    );
  }

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const description = String(form.get("description") ?? "").trim();
    if (description.length < 10) {
      setError("Please describe what happened (at least 10 characters).");
      return;
    }
    const file = form.get("evidence");
    if (file instanceof File && file.size === 0) form.delete("evidence");
    setBusy(true);
    setError(null);
    try {
      const path = target.kind === "agent" ? `/api/agents/${target.id}/report` : `/api/properties/${target.id}/report`;
      setDone(await post<Report>(path, form));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-5 sm:p-6">
      <p className="mb-4 text-sm text-slate-600">
        Reporting {target.kind === "agent" ? "agent" : "listing"}: <strong className="text-slate-900">{target.name}</strong>
      </p>
      <form onSubmit={submit} className="space-y-4">
        <Field label="What happened?" htmlFor="r-reason">
          <Select id="r-reason" name="reason" required defaultValue="">
            <option value="" disabled>
              Choose a reason
            </option>
            {reasons.map((r) => (
              <option key={r} value={r}>
                {humanize(r)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Details" htmlFor="r-desc" hint="Dates, amounts requested, what was said. Don't include passwords or card details.">
          <Textarea id="r-desc" name="description" required minLength={10} maxLength={4000} rows={5} />
        </Field>
        <Field label="Evidence (optional)" htmlFor="r-file" hint="Screenshot or PDF, max 10 MB. Only PropCheck reviewers can see it.">
          <Input id="r-file" name="evidence" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="py-2" />
        </Field>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button type="submit" variant="danger" loading={busy}>
          Submit report
        </Button>
      </form>
    </Card>
  );
}
