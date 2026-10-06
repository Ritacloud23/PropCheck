import { BadgeCheck, Clock, ShieldAlert, ShieldCheck, ShieldOff } from "lucide-react";

import { agentBadge, propertyBadge, type Tone } from "@/lib/badges";
import type { AgentVerificationStatus, PropertyVerificationState } from "@/lib/types";

import { Pill } from "./ui";

const ICON: Record<Tone, typeof ShieldCheck> = {
  verified: ShieldCheck,
  pending: Clock,
  danger: ShieldAlert,
  expired: ShieldOff,
  neutral: ShieldOff,
};

/** Green "Verified Property" — only for a currently valid property verification. */
export function VerifiedPropertyBadge({
  status,
  expiresAt,
}: {
  status: PropertyVerificationState;
  expiresAt?: string | null;
}) {
  const spec = propertyBadge(status, expiresAt);
  const Icon = ICON[spec.tone];
  return (
    <Pill tone={spec.tone} className="bg-white/95 py-1">
      <Icon className="size-3.5" aria-hidden />
      <span title={spec.description}>{spec.label}</span>
    </Pill>
  );
}

/** "Verified Agent" uses a different icon and wording from the property badge on purpose. */
export function VerifiedAgentBadge({
  status,
  expiresAt,
}: {
  status: AgentVerificationStatus;
  expiresAt?: string | null;
}) {
  const spec = agentBadge(status, expiresAt);
  const Icon = spec.tone === "verified" ? BadgeCheck : ICON[spec.tone];
  return (
    <Pill tone={spec.tone} className="py-1">
      <Icon className="size-3.5" aria-hidden />
      <span title={spec.description}>{spec.label}</span>
    </Pill>
  );
}

export function NotYetVerifiedBadge({ label = "Not yet verified" }: { label?: string }) {
  return (
    <Pill tone="neutral" className="py-1">
      <ShieldOff className="size-3.5" aria-hidden />
      {label}
    </Pill>
  );
}
