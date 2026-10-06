"use client";

import { useState } from "react";

import { stateLabel } from "@/lib/format";
import type { ReferenceData } from "@/lib/types";

import { Field, Select } from "./ui";

/**
 * State -> City -> Area selects for GET filter forms. Options come from the API's reference
 * data, so only the states PropCheck currently serves can be chosen.
 */
export function LocationFields({
  reference,
  state,
  city,
  area,
  showArea = true,
}: {
  reference: Pick<ReferenceData, "states" | "locations">;
  state?: string;
  city?: string;
  area?: string;
  showArea?: boolean;
}) {
  const [selectedState, setSelectedState] = useState(state ?? "");
  const cities = reference.locations[selectedState] ?? [];
  const [selectedCity, setSelectedCity] = useState(
    cities.find((c) => c.city.toLowerCase() === (city ?? "").toLowerCase())?.city ?? "",
  );
  const areas = cities.find((c) => c.city === selectedCity)?.areas ?? [];

  return (
    <>
      <Field label="State" htmlFor="f-state">
        <Select
          id="f-state"
          name="state"
          value={selectedState}
          onChange={(e) => {
            setSelectedState(e.target.value);
            setSelectedCity("");
          }}
        >
          <option value="">Any state</option>
          {reference.states.map((s) => (
            <option key={s} value={s}>
              {stateLabel(s)}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="City" htmlFor="f-city">
        <Select
          id="f-city"
          name="city"
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
          disabled={!cities.length}
        >
          <option value="">{cities.length ? "Any city" : "Choose a state first"}</option>
          {cities.map((c) => (
            <option key={c.city} value={c.city}>
              {c.city}
              {c.major ? " (major city)" : ""}
            </option>
          ))}
        </Select>
      </Field>
      {showArea && (
        <Field label="Area / neighbourhood" htmlFor="f-area">
          <Select id="f-area" name="area" defaultValue={area ?? ""} key={selectedCity} disabled={!areas.length}>
            <option value="">{areas.length ? "Any area" : "Choose a city first"}</option>
            {areas.map((a) => (
              <option key={a.area} value={a.area}>
                {a.area} ({a.lga} LGA)
              </option>
            ))}
          </Select>
        </Field>
      )}
    </>
  );
}
