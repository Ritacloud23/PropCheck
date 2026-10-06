"use client";

import { CalendarCheck, Copy, Share2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { errorMessage, post } from "@/lib/api";
import { formatDateTime, formatNaira } from "@/lib/format";
import type { Booking, Reservation, Role, Slot } from "@/lib/types";
import { waShareLink } from "@/lib/whatsapp";

import { Alert, Button, Checkbox, Textarea, buttonClass } from "./ui";

function LoginPrompt({ next, action }: { next: string; action: string }) {
  return (
    <p className="text-sm text-slate-600">
      <Link href={`/login?next=${encodeURIComponent(next)}`} className="font-semibold text-brand-700 hover:underline">
        Log in as a renter
      </Link>{" "}
      to {action}.
    </p>
  );
}

export function BookInspection({
  slots,
  role,
  path,
}: {
  slots: Slot[];
  role: Role | null;
  path: string;
}) {
  const [slotId, setSlotId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<Booking | null>(null);

  if (booked) {
    return (
      <Alert tone="success" title="Inspection requested">
        {formatDateTime(booked.start_time)}. The agent will confirm. Track it in{" "}
        <Link href="/dashboard/renter/bookings" className="font-semibold underline">
          your bookings
        </Link>
        .
      </Alert>
    );
  }
  if (!slots.length) return <p className="text-sm text-slate-600">No inspection times are open right now. Contact the agent.</p>;

  const book = async () => {
    if (!slotId) return;
    setBusy(true);
    setError(null);
    try {
      setBooked(await post<Booking>("/api/inspection-bookings", { slot_id: slotId, renter_note: note || null }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2">
        {slots.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSlotId(s.id)}
            aria-pressed={slotId === s.id}
            className={`rounded-xl border px-3 py-2.5 text-left text-sm transition ${
              slotId === s.id ? "border-brand-600 bg-brand-50 ring-2 ring-brand-600/20" : "border-slate-300 bg-white hover:border-slate-400"
            }`}
          >
            <CalendarCheck className="mr-1.5 inline size-4 text-brand-600" aria-hidden />
            {formatDateTime(s.start_time)}
          </button>
        ))}
      </div>
      {role === "RENTER" ? (
        <>
          <Textarea
            placeholder="Optional note for the agent (e.g. I'll come with my partner)"
            value={note}
            maxLength={1000}
            onChange={(e) => setNote(e.target.value)}
            aria-label="Note for the agent"
          />
          {error && <Alert tone="danger">{error}</Alert>}
          <Button onClick={book} disabled={!slotId} loading={busy} className="w-full">
            Request this inspection
          </Button>
        </>
      ) : role ? (
        <p className="text-sm text-slate-600">Only renter accounts can book inspections.</p>
      ) : (
        <LoginPrompt next={path} action="book an inspection" />
      )}
    </div>
  );
}

export function ReserveProperty({
  propertyId,
  amount,
  terms,
  role,
  path,
}: {
  propertyId: number;
  amount: number;
  terms: string[];
  role: Role | null;
  path: string;
}) {
  const router = useRouter();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (role !== "RENTER") {
    return role ? (
      <p className="text-sm text-slate-600">Only renter accounts can make a reservation.</p>
    ) : (
      <LoginPrompt next={path} action="reserve this property (test mode)" />
    );
  }

  const reserve = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await post<Reservation>("/api/reservations", { property_id: propertyId, accept_terms: true });
      router.push(`/dashboard/renter/reservations?highlight=${res.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-700">
        Reservation amount: <span className="font-semibold">{formatNaira(amount)}</span> (demo only)
      </p>
      <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
        {terms.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <Checkbox
        checked={accepted}
        onChange={(e) => setAccepted(e.target.checked)}
        label="I understand this is a test/demo reservation, not escrow, and accept the terms above."
      />
      {error && <Alert tone="danger">{error}</Alert>}
      <Button onClick={reserve} disabled={!accepted} loading={busy} variant="secondary" className="w-full">
        Create test reservation
      </Button>
    </div>
  );
}

export function ShareButtons({ url, title }: { url: string; title: string }) {
  const [copied, setCopied] = useState(false);
  const text = `Check out this property on PropCheck Nigeria: ${title} ${url}`;
  const copy = async () => {
    await navigator.clipboard.writeText(url).catch(() => undefined);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="flex flex-wrap gap-2">
      <a href={waShareLink(text)} target="_blank" rel="noopener noreferrer" className={buttonClass("secondary", "sm")}>
        <Share2 className="size-4" aria-hidden /> Share on WhatsApp
      </a>
      <button type="button" onClick={copy} className={buttonClass("secondary", "sm")}>
        <Copy className="size-4" aria-hidden /> {copied ? "Link copied" : "Copy link"}
      </button>
    </div>
  );
}
