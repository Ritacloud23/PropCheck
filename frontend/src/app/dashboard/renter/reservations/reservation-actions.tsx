"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ActionButton } from "@/components/action-button";
import { Alert, Button } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";
import type { Reservation } from "@/lib/types";

/** Pay (TEST mode). The simulated provider confirms at once; Paystack test mode redirects to checkout. */
export function PayButton({ reservation }: { reservation: Reservation }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pay = async () => {
    setBusy(true);
    setError(null);
    try {
      const out = await post<{ authorization_url: string | null }>(`/api/reservations/${reservation.id}/pay`);
      if (out.authorization_url) {
        window.location.href = out.authorization_url;
        return;
      }
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <span className="inline-flex flex-col gap-1">
      <Button size="sm" onClick={pay} loading={busy}>
        Pay (test mode)
      </Button>
      {error && <span className="text-xs font-medium text-red-700">{error}</span>}
    </span>
  );
}

/** Handles the return from Paystack TEST checkout (?reference=... or ?trxref=...). */
export function PaystackReturn({ reservations }: { reservations: Reservation[] }) {
  const params = useSearchParams();
  const router = useRouter();
  const ran = useRef(false);
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const reference = params.get("reference") ?? params.get("trxref");

  useEffect(() => {
    if (!reference || ran.current) return;
    const res = reservations.find((r) => r.payment_reference === reference);
    if (!res || res.status !== "PENDING_PAYMENT") return;
    ran.current = true;
    post(`/api/reservations/${res.id}/verify-payment`, { reference })
      .then(() => {
        setMessage({ tone: "success", text: "Test payment confirmed." });
        router.replace("/dashboard/renter/reservations");
        router.refresh();
      })
      .catch((e) => setMessage({ tone: "danger", text: errorMessage(e) }));
  }, [reference, reservations, router]);

  return message ? <Alert tone={message.tone} className="mb-4">{message.text}</Alert> : null;
}

export function ConfirmKeysButton({ id }: { id: number }) {
  return (
    <ActionButton
      path={`/api/reservations/${id}/confirm-keys`}
      label="I've received the keys"
      variant="primary"
      confirm="Confirm you have received the keys? This releases the reservation and cannot be undone."
    />
  );
}
