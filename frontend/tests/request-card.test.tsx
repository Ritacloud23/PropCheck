import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RequestCard } from "@/app/dashboard/renter/house-search/request-card";
import type { AgentPublic, HouseSearchRequest } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const AGENT = {
  id: 7,
  name: "Tamuno Briggs",
  whatsapp_number: "+2348031110004",
  phone_number: "+2348031110004",
  verification_status: "VERIFIED",
  verification_expiry_date: "2027-10-01T00:00:00Z",
} as AgentPublic;

const BASE: HouseSearchRequest = {
  id: 12,
  renter_id: 3,
  name: "Demo Renter",
  phone: "+2348035550005",
  whatsapp_number: null,
  email: null,
  state: "Rivers",
  city: "Port Harcourt",
  local_government_area: "Port Harcourt",
  area: "GRA Phase 2",
  property_type: "FLAT",
  bedrooms: 3,
  budget_min: 3_000_000,
  budget_max: 5_000_000,
  purpose: "RENT",
  preferred_move_in_date: null,
  furnished_preference: "EITHER",
  description: null,
  consent_to_share: true,
  status: "SUBMITTED",
  assigned_agent_id: null,
  assigned_agent: null,
  cancellation_reason: null,
  created_at: "2026-10-01T09:00:00Z",
  updated_at: "2026-10-01T09:00:00Z",
  enquiries: [],
  allowed_actions: ["CANCELLED"],
};

describe("renter house-search request card", () => {
  it("shows naira budget, links to the detail page and offers cancel only when allowed", () => {
    render(<RequestCard request={BASE} linkTitle />);
    expect(screen.getByText(/₦3,000,000 – ₦5,000,000/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /3-bed .* in GRA Phase 2, Port Harcourt/ })).toHaveAttribute(
      "href",
      "/dashboard/renter/house-search/12",
    );
    expect(screen.getByRole("button", { name: "Cancel request" })).toBeInTheDocument();
    expect(screen.queryByText("Your assigned agent")).not.toBeInTheDocument();
  });

  it("shows the assigned agent with WhatsApp contact and hides cancel once contacted", () => {
    render(
      <RequestCard
        request={{ ...BASE, status: "CONTACTED", assigned_agent_id: 7, assigned_agent: AGENT, allowed_actions: ["COMPLETED"] }}
      />,
    );
    expect(screen.getByText("Your assigned agent")).toBeInTheDocument();
    expect(screen.getByText("Verified Agent")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /whatsapp/i })).toHaveAttribute("href", expect.stringContaining("wa.me/2348031110004"));
    expect(screen.queryByRole("button", { name: "Cancel request" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "I found a place" })).toBeInTheDocument();
  });
});
