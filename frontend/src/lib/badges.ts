import type { AgentVerificationStatus, PropertyVerificationState } from "./types";

export type Tone = "verified" | "pending" | "danger" | "neutral" | "expired";

export interface BadgeSpec {
  label: string;
  tone: Tone;
  description: string;
}

/** Agent and property badges intentionally use different wording so they are never confused. */
export function agentBadge(status: AgentVerificationStatus, expiresAt?: string | null, now = new Date()): BadgeSpec {
  const expired = status === "VERIFIED" && !!expiresAt && new Date(expiresAt) <= now;
  if (status === "VERIFIED" && !expired)
    return { label: "Verified Agent", tone: "verified", description: "Identity and business details checked by PropCheck." };
  if (status === "EXPIRED" || expired)
    return { label: "Agent verification expired", tone: "expired", description: "This agent's verification is out of date." };
  if (status === "SUSPENDED")
    return { label: "Agent suspended", tone: "danger", description: "Suspended after a review. Do not pay this agent." };
  if (status === "REJECTED") return { label: "Agent not verified", tone: "danger", description: "Verification was declined." };
  if (status === "SUBMITTED" || status === "IN_REVIEW")
    return { label: "Agent verification pending", tone: "pending", description: "PropCheck is reviewing this agent." };
  return { label: "Agent not yet verified", tone: "neutral", description: "This agent has not been verified." };
}

export function propertyBadge(
  status: PropertyVerificationState,
  expiresAt?: string | null,
  now = new Date(),
): BadgeSpec {
  const expired = status === "VERIFIED" && (!expiresAt || new Date(expiresAt) <= now);
  if (status === "VERIFIED" && !expired)
    return {
      label: "Verified Property",
      tone: "verified",
      description: "Authority, location and fees checked by a PropCheck reviewer.",
    };
  if (status === "EXPIRED" || expired)
    return { label: "Verification expired", tone: "expired", description: "The checks on this listing are out of date." };
  if (status === "REJECTED")
    return { label: "Verification failed", tone: "danger", description: "This listing did not pass verification." };
  if (status === "SUBMITTED" || status === "IN_REVIEW" || status === "INSPECTION_BOOKED")
    return { label: "Verification in progress", tone: "pending", description: "A PropCheck reviewer is checking this listing." };
  return { label: "Not yet verified", tone: "neutral", description: "PropCheck has not checked this listing." };
}

export const STATUS_TONE: Record<string, Tone> = {
  VERIFIED: "verified",
  CONFIRMED: "verified",
  COMPLETED: "verified",
  RELEASED: "verified",
  RESOLVED: "verified",
  ACCEPTED: "verified",
  PASSED: "verified",
  ASSIGNED: "verified",
  CONTACTED: "verified",
  RESPONDED: "verified",
  SUBMITTED: "pending",
  IN_REVIEW: "pending",
  INSPECTION_BOOKED: "pending",
  REQUESTED: "pending",
  MATCHING: "pending",
  PENDING_PAYMENT: "pending",
  PENDING_RELEASE: "pending",
  PENDING: "pending",
  OPEN: "pending",
  UPLOADED: "pending",
  REVIEWED: "pending",
  REJECTED: "danger",
  DECLINED: "danger",
  SUSPENDED: "danger",
  FAILED: "danger",
  REFUNDED: "neutral",
  CANCELLED: "neutral",
  EXPIRED: "expired",
};
