import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LocationFields } from "@/components/location-fields";
import { NEARBY_NOTICE, NearbyPlaces } from "@/components/nearby-places";
import { directionsUrl, formatDistance, placeLabel } from "@/lib/format";
import type { NearbyPlace, ReferenceData } from "@/lib/types";

// Leaflet needs a real browser; the map is loaded with next/dynamic, so stub it out.
vi.mock("next/dynamic", () => ({
  default: () =>
    function MapStub({ places }: { places: NearbyPlace[] }) {
      return <div data-testid="map">{places.length} markers</div>;
    },
}));

function place(id: number, name: string, category: NearbyPlace["category"], km: number, extra: Partial<NearbyPlace> = {}): NearbyPlace {
  return {
    id,
    name,
    category,
    description: null,
    address: `${id} Market Road, GRA Phase 2`,
    area: "GRA Phase 2",
    city: "Port Harcourt",
    local_government_area: "Port Harcourt",
    state: "Rivers",
    latitude: 4.816 + km / 111,
    longitude: 7.001,
    phone_number: null,
    website_url: null,
    opening_hours: null,
    distance_km: km,
    distance_m: Math.round(km * 1000),
    distance_label: "",
    is_demo_data: false,
    ...extra,
  };
}

const PLACES = [
  place(1, "Pepper Soup Place", "RESTAURANT", 0.35, { opening_hours: "Daily 10:00–22:00", phone_number: "+2348000001234" }),
  place(2, "GRA Daily Market", "MARKET", 0.8, { is_demo_data: true }),
  place(3, "Grace Assembly", "CHURCH", 1.24),
  place(4, "Palm Lounge", "CLUB", 2.06),
];
const ORIGIN = { latitude: 4.816, longitude: 7.001 };

function renderNearby(places = PLACES) {
  return render(
    <NearbyPlaces
      places={places}
      origin={ORIGIN}
      radiusKm={3}
      reportReasons={["WRONG_LOCATION", "PERMANENTLY_CLOSED"]}
      loggedIn={false}
      loginNext="/properties/x#nearby"
    />,
  );
}

describe("formatDistance", () => {
  it.each([
    [0.004, "10 m"],
    [0.25, "250 m"],
    [0.8549, "850 m"],
    [0.996, "1.0 km"],
    [1, "1.0 km"],
    [1.26, "1.3 km"],
    [12.04, "12.0 km"],
  ])("formats %s km as %s", (km, label) => {
    expect(formatDistance(km)).toBe(label);
  });
});

describe("directions and labels", () => {
  it("builds a Google Maps directions URL, from the property when given", () => {
    expect(directionsUrl({ latitude: 4.8, longitude: 7.01 })).toBe(
      "https://www.google.com/maps/dir/?api=1&destination=4.8%2C7.01",
    );
    expect(directionsUrl({ latitude: 4.8, longitude: 7.01 }, ORIGIN)).toContain("origin=4.816%2C7.001");
  });
  it("prefers the area in place labels", () => {
    expect(placeLabel({ area: "GRA Phase 2", city: "Port Harcourt", state: "Rivers" })).toBe("GRA Phase 2, Port Harcourt, Rivers");
    expect(placeLabel({ area: null, city: "Enugu", state: "Enugu" })).toBe("Enugu");
  });
});

describe("NearbyPlaces (property page section)", () => {
  it("lists places nearest first with distance, address, hours, phone and directions", () => {
    renderNearby();
    const items = within(screen.getByRole("list", { name: "Nearby places" })).getAllByRole("listitem");
    expect(items.map((li) => li.querySelector("p")?.textContent)).toEqual([
      "Pepper Soup Place",
      "GRA Daily Market",
      "Grace Assembly",
      "Palm Lounge",
    ]);
    expect(screen.getAllByTestId("distance").map((d) => d.textContent)).toEqual([
      "350 m away",
      "800 m away",
      "1.2 km away",
      "2.1 km away",
    ]);
    expect(screen.getByText("Daily 10:00–22:00")).toBeInTheDocument();
    expect(screen.getByText("+234 800 000 1234")).toBeInTheDocument();
    expect(screen.getByText("1 Market Road, GRA Phase 2")).toBeInTheDocument();
    const directions = screen.getAllByRole("link", { name: /Get directions/ });
    expect(directions).toHaveLength(4);
    expect(directions[0].getAttribute("href")).toContain("destination=");
    expect(screen.getByTestId("map")).toHaveTextContent("4 markers");
  });

  it("filters by category tabs", () => {
    renderNearby();
    fireEvent.click(screen.getByRole("tab", { name: /Churches/ }));
    expect(screen.getByRole("tab", { name: /Churches/ })).toHaveAttribute("aria-selected", "true");
    const items = within(screen.getByRole("list", { name: "Nearby places" })).getAllByRole("listitem");
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent("Grace Assembly");
    expect(screen.getByTestId("map")).toHaveTextContent("1 markers");
  });

  it("shows an empty state for a category with no places", () => {
    renderNearby([PLACES[0]]);
    fireEvent.click(screen.getByRole("tab", { name: /Clubs/ }));
    expect(screen.getByText("No clubs found within 3 km")).toBeInTheDocument();
  });

  it("shows an empty state when nothing is nearby at all", () => {
    renderNearby([]);
    expect(screen.getByText("No places found within 3 km")).toBeInTheDocument();
  });

  it("labels demo data, carries the notice and never claims places are verified", () => {
    renderNearby();
    expect(screen.getAllByText("Demo data")).toHaveLength(1);
    expect(document.body.textContent).toContain(NEARBY_NOTICE);
    expect(screen.getByText("not verified")).toBeInTheDocument();
    expect(screen.queryByText(/Verified (place|market|restaurant)/i)).not.toBeInTheDocument();
  });

  it("asks logged-out users to log in before reporting incorrect information", () => {
    renderNearby();
    fireEvent.click(screen.getAllByRole("button", { name: /Report incorrect information/ })[0]);
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/login?next=%2Fproperties%2Fx%23nearby");
  });
});

describe("LocationFields (search filters)", () => {
  const reference: Pick<ReferenceData, "states" | "locations"> = {
    states: ["Lagos", "Rivers", "Enugu", "Anambra", "Imo"],
    locations: {
      Lagos: [{ city: "Lagos", major: true, latitude: 6.5, longitude: 3.4, areas: [{ area: "Lekki", lga: "Eti-Osa", latitude: 6.4, longitude: 3.5 }] }],
      Rivers: [
        {
          city: "Port Harcourt",
          major: true,
          latitude: 4.8,
          longitude: 7.0,
          areas: [{ area: "GRA Phase 2", lga: "Port Harcourt", latitude: 4.81, longitude: 7.0 }],
        },
        { city: "Bonny", major: false, latitude: 4.45, longitude: 7.17, areas: [] },
      ],
      Enugu: [],
      Anambra: [],
      Imo: [],
    },
  };

  it("offers only the five launch states", () => {
    render(<LocationFields reference={reference} />);
    const options = within(screen.getByLabelText("State")).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Any state", "Lagos", "Rivers", "Enugu", "Anambra", "Imo"]);
    expect(options).not.toContain("FCT");
    expect(options).not.toContain("Abuja (FCT)");
  });

  it("lists Port Harcourt as the major city under Rivers, then its areas", () => {
    render(<LocationFields reference={reference} />);
    fireEvent.change(screen.getByLabelText("State"), { target: { value: "Rivers" } });
    const cities = within(screen.getByLabelText("City")).getAllByRole("option").map((o) => o.textContent);
    expect(cities).toEqual(["Any city", "Port Harcourt (major city)", "Bonny"]);
    fireEvent.change(screen.getByLabelText("City"), { target: { value: "Port Harcourt" } });
    const areas = within(screen.getByLabelText("Area / neighbourhood")).getAllByRole("option").map((o) => o.textContent);
    expect(areas).toContain("GRA Phase 2 (Port Harcourt LGA)");
  });
});
