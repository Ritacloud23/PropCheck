import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentCard } from "@/components/agent-card";
import { FeeBreakdown } from "@/components/fee-breakdown";
import { WhatsAppButton } from "@/components/whatsapp-button";
import type { AgentPublic } from "@/lib/types";

const agent: AgentPublic = {
  id: 7,
  name: "Adaeze Okafor",
  agency_name: "Lekki Prime Realty",
  bio: "",
  profile_photo_url: null,
  phone_number: null,
  whatsapp_number: null,
  email: null,
  contact_public: false,
  states_covered: ["Lagos"],
  cities_covered: ["Lekki"],
  lgas_covered: [],
  property_types: ["FLAT"],
  service_types: ["RENTAL"],
  budget_min: null,
  budget_max: null,
  years_experience: 9,
  verification_status: "VERIFIED",
  is_verified: true,
  verification_date: null,
  verification_expiry_date: "2099-01-01T00:00:00Z",
  active_listings: 2,
  completed_connections: 0,
  average_rating: null,
  total_reviews: 0,
  complaint_status: "NO_OPEN_COMPLAINTS",
  response_time_hours: null,
  joined_at: "2026-01-01T00:00:00Z",
};

describe("AgentCard contact privacy", () => {
  it("hides phone and WhatsApp when the agent has not consented", () => {
    render(<AgentCard agent={agent} />);
    expect(screen.queryByText(/WhatsApp/)).not.toBeInTheDocument();
    expect(document.querySelector('a[href^="https://wa.me"]')).toBeNull();
    expect(screen.getByRole("link", { name: "Request help" })).toHaveAttribute("href", "/find-an-agent?agent=7");
  });
  it("shows a WhatsApp link when consented", () => {
    render(
      <AgentCard
        agent={{ ...agent, contact_public: true, phone_number: "+2348031110001", whatsapp_number: "+2348031110001" }}
      />,
    );
    const link = screen.getByRole("link", { name: /WhatsApp/ });
    expect(link.getAttribute("href")).toMatch(/^https:\/\/wa\.me\/2348031110001\?text=Hello%20Adaeze/);
  });
});

describe("WhatsAppButton", () => {
  it("renders nothing without a number", () => {
    const { container } = render(<WhatsAppButton number={null} message="hi" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("FeeBreakdown", () => {
  it("lists every fee and the server-computed total", () => {
    render(
      <FeeBreakdown
        fees={{
          rent_amount: 3_500_000,
          agency_fee: 350_000,
          legal_fee: 350_000,
          caution_fee: 200_000,
          other_fees: 50_000,
          other_fees_description: "Estate due",
          total_move_in_cost: 4_450_000,
        }}
      />,
    );
    expect(screen.getByText("₦3,500,000")).toBeInTheDocument();
    expect(screen.getAllByText("₦350,000")).toHaveLength(2);
    expect(screen.getByText("Estate due")).toBeInTheDocument();
    expect(within(screen.getByTestId("fee-total")).getByText("₦4,450,000")).toBeInTheDocument();
  });
});
