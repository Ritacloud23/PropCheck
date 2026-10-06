"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { errorMessage, post } from "@/lib/api";

import { Button, Input, Textarea } from "./ui";

type Variant = "primary" | "secondary" | "danger" | "ghost";

/**
 * Posts to an API endpoint, then refreshes the server-rendered page so lists and statuses update.
 * With `reason`, asks for a reason first (required or optional); with `dateField`, asks for a date.
 */
export function ActionButton({
  path,
  body,
  label,
  variant = "secondary",
  size = "sm",
  reason,
  dateField,
  confirm,
  onDone,
}: {
  path: string;
  body?: Record<string, unknown>;
  label: ReactNode;
  variant?: Variant;
  size?: "sm" | "md";
  reason?: { required: boolean; label?: string; field?: string };
  dateField?: { name: string; label: string; type?: "date" | "datetime-local"; required?: boolean };
  confirm?: string;
  onDone?: (result: unknown) => void;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsInput = !!reason || !!dateField;

  const run = async () => {
    if (reason?.required && text.trim().length < 3) {
      setError("Please give a reason (at least 3 characters).");
      return;
    }
    if (dateField?.required && !date) {
      setError(`Please choose ${dateField.label.toLowerCase()}.`);
      return;
    }
    if (confirm && !window.confirm(confirm)) return;
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { ...body };
      if (reason && text.trim()) payload[reason.field ?? "reason"] = text.trim();
      if (dateField && date) payload[dateField.name] = new Date(date).toISOString();
      const result = await post(path, payload);
      setOpen(false);
      setText("");
      onDone?.(result);
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (needsInput && open) {
    return (
      <div className="w-full space-y-2 rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200 sm:min-w-72">
        {dateField && (
          <label className="block text-xs font-medium text-slate-700">
            {dateField.label}
            <Input type={dateField.type ?? "date"} value={date} onChange={(e) => setDate(e.target.value)} className="mt-1" />
          </label>
        )}
        {reason && (
          <label className="block text-xs font-medium text-slate-700">
            {reason.label ?? (reason.required ? "Reason (required)" : "Note (optional)")}
            <Textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} className="mt-1 min-h-16" />
          </label>
        )}
        {error && <p className="text-xs font-medium text-red-700">{error}</p>}
        <div className="flex gap-2">
          <Button size="sm" variant={variant === "ghost" ? "secondary" : variant} loading={busy} onClick={run}>
            {label}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <span className="inline-flex flex-col gap-1">
      <Button size={size} variant={variant} loading={busy} onClick={needsInput ? () => setOpen(true) : run}>
        {label}
      </Button>
      {error && !open && <span className="max-w-60 text-xs font-medium text-red-700">{error}</span>}
    </span>
  );
}
