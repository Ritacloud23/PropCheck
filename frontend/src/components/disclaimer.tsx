import { AlertTriangle, Info } from "lucide-react";

import { cn } from "@/lib/utils";

export const DISCLAIMER =
  "PropCheck verifies the documents, identity information and inspection evidence listed in this report. It is not a substitute for a formal title search, legal advice or an official land-registry search. Users should verify payment terms before sending money.";
export const PAYMENT_WARNING = "Do not send money before confirming the property, agent authority and payment terms.";

export function Disclaimer({ className }: { className?: string }) {
  return (
    <div className={cn("flex gap-3 rounded-xl bg-slate-100 px-4 py-3 text-xs leading-relaxed text-slate-600", className)}>
      <Info className="mt-0.5 size-4 shrink-0 text-slate-500" aria-hidden />
      <p>{DISCLAIMER}</p>
    </div>
  );
}

export function SafetyWarning({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900",
        className,
      )}
      role="note"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <p>{PAYMENT_WARNING}</p>
    </div>
  );
}
