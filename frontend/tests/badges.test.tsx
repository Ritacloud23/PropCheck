import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerifiedAgentBadge, VerifiedPropertyBadge } from "@/components/badges";
import { agentBadge, propertyBadge } from "@/lib/badges";

const NOW = new Date("2026-10-06T12:00:00Z");
const FUTURE = "2027-01-01T00:00:00Z";
const PAST = "2026-01-01T00:00:00Z";

describe("property badge", () => {
  it("is green 'Verified Property' only while valid", () => {
    expect(propertyBadge("VERIFIED", FUTURE, NOW)).toMatchObject({ label: "Verified Property", tone: "verified" });
  });
  it("shows expired when the expiry date has passed or is missing", () => {
    expect(propertyBadge("VERIFIED", PAST, NOW).label).toBe("Verification expired");
    expect(propertyBadge("VERIFIED", null, NOW).label).toBe("Verification expired");
    expect(propertyBadge("EXPIRED", null, NOW).tone).toBe("expired");
  });
  it("distinguishes in-progress, failed and not-submitted", () => {
    expect(propertyBadge("IN_REVIEW", null, NOW).tone).toBe("pending");
    expect(propertyBadge("INSPECTION_BOOKED", null, NOW).tone).toBe("pending");
    expect(propertyBadge("REJECTED", null, NOW).tone).toBe("danger");
    expect(propertyBadge("NOT_SUBMITTED", null, NOW).label).toBe("Not yet verified");
  });
});

describe("agent badge", () => {
  it("uses agent-specific wording, never the property label", () => {
    const spec = agentBadge("VERIFIED", FUTURE, NOW);
    expect(spec.label).toBe("Verified Agent");
    expect(spec.label).not.toBe(propertyBadge("VERIFIED", FUTURE, NOW).label);
  });
  it("handles expiry, suspension and pending states", () => {
    expect(agentBadge("VERIFIED", PAST, NOW).tone).toBe("expired");
    expect(agentBadge("SUSPENDED", null, NOW)).toMatchObject({ label: "Agent suspended", tone: "danger" });
    expect(agentBadge("SUBMITTED", null, NOW).tone).toBe("pending");
    expect(agentBadge("DRAFT", null, NOW).label).toBe("Agent not yet verified");
  });
});

describe("badge components", () => {
  it("render the right label", () => {
    render(
      <>
        <VerifiedAgentBadge status="VERIFIED" expiresAt={FUTURE} />
        <VerifiedPropertyBadge status="SUBMITTED" />
      </>,
    );
    expect(screen.getByText("Verified Agent")).toBeInTheDocument();
    expect(screen.getByText("Verification in progress")).toBeInTheDocument();
    expect(screen.queryByText("Verified Property")).not.toBeInTheDocument();
  });
});
