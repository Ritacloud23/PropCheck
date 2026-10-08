"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, Button, Field, Input, Select } from "@/components/ui";
import { api, errorMessage, post } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { AvailabilityStatus } from "@/lib/types";

function useAction() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      router.refresh();
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, run };
}

export function MediaUpload({ propertyId, disabled }: { propertyId: number; disabled?: boolean }) {
  const { busy, error, run } = useAction();
  const upload = (files: FileList | null) => {
    if (!files?.length) return;
    run(async () => {
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        await post(`/api/properties/${propertyId}/media`, fd);
      }
    });
  };
  return (
    <div className="space-y-2">
      <label className={`inline-flex cursor-pointer items-center rounded-xl px-4 py-2.5 text-sm font-semibold ring-1 ring-slate-300 ${disabled ? "opacity-50" : "hover:bg-slate-50"}`}>
        {busy ? "Uploading…" : "Add photos"}
        <input
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          disabled={disabled || busy}
          onChange={(e) => upload(e.target.files)}
        />
      </label>
      <p className="text-xs text-slate-500">JPG, PNG or WEBP · max 5 MB each · up to 15 photos</p>
      {error && <Alert tone="danger">{error}</Alert>}
    </div>
  );
}

export function DocumentUpload({ propertyId, documentTypes }: { propertyId: number; documentTypes: string[] }) {
  const { busy, error, run } = useAction();
  const [type, setType] = useState("AUTHORITY_LETTER");
  const [file, setFile] = useState<File | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const submit = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("document_type", type);
    if (await run(() => post(`/api/properties/${propertyId}/documents`, fd))) {
      setFile(null);
      setInputKey((k) => k + 1);
    }
  };
  return (
    <div className="space-y-3 rounded-xl bg-slate-50 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Document type" htmlFor="dtype">
          <Select id="dtype" value={type} onChange={(e) => setType(e.target.value)}>
            {documentTypes.map((t) => (
              <option key={t} value={t}>
                {humanize(t)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="File" htmlFor="dfile" hint="PDF, JPG, PNG, WEBP · max 10 MB · private">
          <Input
            key={inputKey}
            id="dfile"
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="py-2"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
      </div>
      {error && <Alert tone="danger">{error}</Alert>}
      <Button size="sm" onClick={submit} disabled={!file} loading={busy}>
        Upload document
      </Button>
    </div>
  );
}

export function SlotCreator({ propertyId }: { propertyId: number }) {
  const { busy, error, run } = useAction();
  const [date, setDate] = useState("");
  const [time, setTime] = useState("10:00");
  const [minutes, setMinutes] = useState(60);
  const submit = () => {
    if (!date) return;
    const start = new Date(`${date}T${time}`);
    const end = new Date(start.getTime() + minutes * 60_000);
    run(() => post(`/api/properties/${propertyId}/inspection-slots`, { start_time: start.toISOString(), end_time: end.toISOString() }));
  };
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Date" htmlFor="sdate">
          <Input id="sdate" type="date" value={date} min={new Date().toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <Field label="Start time" htmlFor="stime">
          <Input id="stime" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </Field>
        <Field label="Length" htmlFor="slen">
          <Select id="slen" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
            <option value={30}>30 minutes</option>
            <option value={60}>1 hour</option>
            <option value={90}>1½ hours</option>
            <option value={120}>2 hours</option>
          </Select>
        </Field>
      </div>
      {error && <Alert tone="danger">{error}</Alert>}
      <Button size="sm" onClick={submit} disabled={!date} loading={busy}>
        Add inspection slot
      </Button>
    </div>
  );
}

export function ListingControls({
  propertyId,
  availability,
  isListed,
}: {
  propertyId: number;
  availability: AvailabilityStatus;
  isListed: boolean;
}) {
  const { busy, error, run } = useAction();
  const patch = (body: Record<string, unknown>) => run(() => api(`/api/properties/${propertyId}`, { method: "PATCH", body }));
  return (
    <div className="space-y-3">
      <Field label="Availability" htmlFor="avail">
        <Select id="avail" value={availability} disabled={busy} onChange={(e) => patch({ availability_status: e.target.value })}>
          {(["AVAILABLE", "RESERVED", "LET", "UNAVAILABLE"] as const).map((s) => (
            <option key={s} value={s}>
              {humanize(s)}
            </option>
          ))}
        </Select>
      </Field>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={isListed} disabled={busy} onChange={(e) => patch({ is_listed: e.target.checked })} className="accent-brand-600" />
        Show this listing publicly
      </label>
      {error && <Alert tone="danger">{error}</Alert>}
    </div>
  );
}
