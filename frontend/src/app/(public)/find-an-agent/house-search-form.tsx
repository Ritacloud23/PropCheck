"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Alert, Button, Card, Checkbox, Field, Input, Select, Textarea } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";
import { propertyTypeLabel, stateLabel } from "@/lib/format";
import { clean, houseSearchSchema, type HouseSearchInput } from "@/lib/schemas";
import type { HouseSearchRequest, ReferenceData, User } from "@/lib/types";

export function HouseSearchForm({ reference, user }: { reference: ReferenceData; user: User }) {
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<HouseSearchRequest | null>(null);
  const { register, handleSubmit, formState, control } = useForm<HouseSearchInput>({
    resolver: zodResolver(houseSearchSchema),
    defaultValues: {
      name: user.full_name,
      phone: user.phone ?? "",
      email: user.email,
      state: "Lagos",
      city: "Lagos",
      property_type: "FLAT",
      bedrooms: 1,
      purpose: "RENT",
      furnished_preference: "EITHER",
      consent_to_share: false,
    },
  });
  const [state, city] = useWatch({ control, name: ["state", "city"] });
  const cities = reference.locations[state] ?? [];
  const areas = cities.find((c) => c.city === city)?.areas ?? [];
  const e = formState.errors;

  if (created) {
    return (
      <Alert tone="success" title="Request received">
        <p>
          PropCheck will match you with a verified agent who covers {created.city}. Only that agent will see your request.
          Track progress in{" "}
          <Link href="/dashboard/renter/house-search" className="font-semibold underline">
            your dashboard
          </Link>
          .
        </p>
      </Alert>
    );
  }

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    try {
      setCreated(await post<HouseSearchRequest>("/api/house-search-requests", clean(data)));
    } catch (err) {
      setError(errorMessage(err));
    }
  });

  return (
    <Card className="p-5 sm:p-6">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Your name" htmlFor="name" error={e.name?.message}>
            <Input id="name" {...register("name")} />
          </Field>
          <Field label="Phone" htmlFor="phone" error={e.phone?.message}>
            <Input id="phone" type="tel" inputMode="tel" {...register("phone")} />
          </Field>
          <Field label="WhatsApp (if different)" htmlFor="wa" error={e.whatsapp_number?.message}>
            <Input id="wa" type="tel" inputMode="tel" {...register("whatsapp_number")} />
          </Field>
          <Field label="Email" htmlFor="hs-email" error={e.email?.message}>
            <Input id="hs-email" type="email" {...register("email")} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="I want to" htmlFor="purpose">
            <Select id="purpose" {...register("purpose")}>
              <option value="RENT">Rent</option>
              <option value="PURCHASE">Buy</option>
            </Select>
          </Field>
          <Field label="State" htmlFor="hs-state" error={e.state?.message}>
            <Select id="hs-state" {...register("state")}>
              {reference.states.map((s) => (
                <option key={s} value={s}>
                  {stateLabel(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="City" htmlFor="hs-city" error={e.city?.message}>
            <Select id="hs-city" {...register("city")}>
              <option value="">Choose a city</option>
              {cities.map((c) => (
                <option key={c.city} value={c.city}>
                  {c.city}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Preferred area (optional)" htmlFor="hs-area">
            <Input id="hs-area" list="hs-areas" placeholder="e.g. GRA Phase 2" {...register("area")} />
            <datalist id="hs-areas">
              {areas.map((a) => (
                <option key={a.area} value={a.area} />
              ))}
            </datalist>
          </Field>
          <Field label="Property type" htmlFor="hs-type">
            <Select id="hs-type" {...register("property_type")}>
              {reference.property_types.map((t) => (
                <option key={t} value={t}>
                  {propertyTypeLabel(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Bedrooms" htmlFor="hs-beds" error={e.bedrooms?.message}>
            <Input id="hs-beds" type="number" min={0} max={20} inputMode="numeric" {...register("bedrooms")} />
          </Field>
          <Field label="Furnishing" htmlFor="hs-furn">
            <Select id="hs-furn" {...register("furnished_preference")}>
              <option value="EITHER">Either</option>
              <option value="FURNISHED">Furnished</option>
              <option value="UNFURNISHED">Unfurnished</option>
            </Select>
          </Field>
          <Field label="Min budget (₦/year)" htmlFor="hs-min" error={e.budget_min?.message}>
            <Input id="hs-min" type="number" min={0} step={50000} inputMode="numeric" {...register("budget_min")} />
          </Field>
          <Field label="Max budget (₦/year)" htmlFor="hs-max" error={e.budget_max?.message}>
            <Input id="hs-max" type="number" min={0} step={50000} inputMode="numeric" {...register("budget_max")} />
          </Field>
          <Field label="Move-in date" htmlFor="hs-date">
            <Input id="hs-date" type="date" {...register("preferred_move_in_date")} />
          </Field>
        </div>
        <Field label="Anything else?" htmlFor="hs-desc" error={e.description?.message}>
          <Textarea id="hs-desc" placeholder="Close to work in VI, need steady water, no shared compound…" {...register("description")} />
        </Field>
        <div>
          <Checkbox
            {...register("consent_to_share")}
            label="I agree that PropCheck may share this request and my contact details with the verified agent it assigns to me."
          />
          {e.consent_to_share && <p className="mt-1 text-xs font-medium text-red-700">{e.consent_to_share.message}</p>}
        </div>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button type="submit" size="lg" loading={formState.isSubmitting} className="w-full sm:w-auto">
          Send request
        </Button>
      </form>
    </Card>
  );
}
