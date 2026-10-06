"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Alert, Button, Card, CardHeader, Checkbox, Field, Input, Select, Textarea } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { formatNaira, propertyTypeLabel, stateLabel } from "@/lib/format";
import { clean, propertySchema, type PropertyInput } from "@/lib/schemas";
import type { PropertyDetail, ReferenceData } from "@/lib/types";

const FEE_FIELDS = ["rent_amount", "agency_fee", "legal_fee", "caution_fee", "other_fees"] as const;

export function PropertyForm({ property, reference }: { property?: PropertyDetail; reference: ReferenceData }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const { register, handleSubmit, formState, control, setValue, getValues } = useForm<PropertyInput>({
    resolver: zodResolver(propertySchema),
    defaultValues: property
      ? {
          title: property.title,
          description: property.description,
          address: property.address,
          landmark: property.landmark ?? "",
          state: property.state,
          city: property.city,
          area: property.area ?? "",
          local_government_area: property.local_government_area ?? "",
          latitude: property.latitude ?? "",
          longitude: property.longitude ?? "",
          property_type: property.property_type,
          bedrooms: property.bedrooms,
          bathrooms: property.bathrooms,
          furnished: property.furnished,
          ...property.fees,
          other_fees_description: property.fees.other_fees_description ?? "",
        }
      : { state: "Lagos", property_type: "FLAT", bedrooms: 1, bathrooms: 1, furnished: false, agency_fee: 0, legal_fee: 0, caution_fee: 0, other_fees: 0 },
  });
  const e = formState.errors;
  const [state, city, ...fees] = useWatch({ control, name: ["state", "city", ...FEE_FIELDS] });
  // Preview only — the API always recalculates the total itself.
  const previewTotal = fees.reduce<number>((sum, v) => sum + (Number(v) || 0), 0);
  const cities = reference.locations[state as string] ?? [];
  const areas = cities.find((c) => c.city === city)?.areas ?? [];

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    setSaved(false);
    try {
      const body = clean(data);
      if (property) {
        await api(`/api/properties/${property.id}`, { method: "PATCH", body });
        setSaved(true);
        router.refresh();
      } else {
        const created = await api<PropertyDetail>("/api/properties", { method: "POST", body });
        router.push(`/dashboard/agent/properties/${created.id}`);
      }
    } catch (err) {
      setError(errorMessage(err));
    }
  });

  return (
    <Card>
      <CardHeader title={property ? "Listing details" : "New listing"} />
      <form onSubmit={onSubmit} className="space-y-5 p-5" noValidate>
        <Field label="Title" htmlFor="title" error={e.title?.message} hint="e.g. Newly built 2-bedroom flat in Woji, Port Harcourt">
          <Input id="title" {...register("title")} />
        </Field>
        <Field label="Description" htmlFor="desc">
          <Textarea id="desc" rows={4} {...register("description")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Street address" htmlFor="address" error={e.address?.message} hint="Shown to renters on the listing">
            <Input id="address" {...register("address")} />
          </Field>
          <Field label="Landmark" htmlFor="landmark">
            <Input id="landmark" {...register("landmark")} />
          </Field>
          <Field label="State" htmlFor="pstate" error={e.state?.message}>
            <Select id="pstate" {...register("state")}>
              {reference.states.map((s) => (
                <option key={s} value={s}>
                  {stateLabel(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="City" htmlFor="pcity" error={e.city?.message}>
            <Select id="pcity" {...register("city")}>
              <option value="">Choose a city</option>
              {cities.map((c) => (
                <option key={c.city} value={c.city}>
                  {c.city}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Area / neighbourhood" htmlFor="parea" hint="Pick from the list or type a new area">
            <Input
              id="parea"
              list="pareas"
              {...register("area", {
                onChange: (ev) => {
                  // Known area: fill in its LGA and, if empty, approximate map coordinates.
                  const match = areas.find((a) => a.area === ev.target.value);
                  if (!match) return;
                  setValue("local_government_area", match.lga);
                  if (!getValues("latitude")) setValue("latitude", match.latitude);
                  if (!getValues("longitude")) setValue("longitude", match.longitude);
                },
              })}
            />
            <datalist id="pareas">
              {areas.map((a) => (
                <option key={a.area} value={a.area} />
              ))}
            </datalist>
          </Field>
          <Field label="LGA" htmlFor="plga">
            <Input id="plga" {...register("local_government_area")} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Latitude" htmlFor="lat" error={e.latitude?.message}>
              <Input id="lat" type="number" step="any" {...register("latitude")} />
            </Field>
            <Field label="Longitude" htmlFor="lng" error={e.longitude?.message}>
              <Input id="lng" type="number" step="any" {...register("longitude")} />
            </Field>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Type" htmlFor="ptype">
            <Select id="ptype" {...register("property_type")}>
              {reference.property_types.map((t) => (
                <option key={t} value={t}>
                  {propertyTypeLabel(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Bedrooms" htmlFor="beds" error={e.bedrooms?.message}>
            <Input id="beds" type="number" min={0} max={20} {...register("bedrooms")} />
          </Field>
          <Field label="Bathrooms" htmlFor="baths" error={e.bathrooms?.message}>
            <Input id="baths" type="number" min={0} max={20} {...register("bathrooms")} />
          </Field>
        </div>
        <Checkbox {...register("furnished")} label="Furnished" />

        <fieldset className="rounded-xl bg-slate-50 p-4">
          <legend className="px-1 text-sm font-semibold text-slate-900">Fees (whole naira)</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Annual rent" htmlFor="rent" error={e.rent_amount?.message}>
              <Input id="rent" type="number" min={0} inputMode="numeric" {...register("rent_amount")} />
            </Field>
            <Field label="Agency fee" htmlFor="agency_fee" error={e.agency_fee?.message}>
              <Input id="agency_fee" type="number" min={0} inputMode="numeric" {...register("agency_fee")} />
            </Field>
            <Field label="Legal / agreement fee" htmlFor="legal_fee" error={e.legal_fee?.message}>
              <Input id="legal_fee" type="number" min={0} inputMode="numeric" {...register("legal_fee")} />
            </Field>
            <Field label="Caution deposit" htmlFor="caution_fee" error={e.caution_fee?.message}>
              <Input id="caution_fee" type="number" min={0} inputMode="numeric" {...register("caution_fee")} />
            </Field>
            <Field label="Other fees" htmlFor="other_fees" error={e.other_fees?.message}>
              <Input id="other_fees" type="number" min={0} inputMode="numeric" {...register("other_fees")} />
            </Field>
            <Field label="What are the other fees?" htmlFor="ofd">
              <Input id="ofd" placeholder="e.g. Estate service charge" {...register("other_fees_description")} />
            </Field>
          </div>
          <p className="mt-4 text-sm text-slate-700">
            Total move-in cost renters will see: <strong className="tabular-nums">{formatNaira(previewTotal)}</strong>
          </p>
        </fieldset>
        {property?.verification.is_currently_verified && (
          <Alert tone="warning">
            This listing is verified. Changing the address, area, type, bedrooms, rent or any fee will mark the verification as
            expired until it is re-checked.
          </Alert>
        )}
        {error && <Alert tone="danger">{error}</Alert>}
        {saved && <Alert tone="success">Saved.</Alert>}
        <Button type="submit" loading={formState.isSubmitting}>
          {property ? "Save changes" : "Create listing"}
        </Button>
      </form>
    </Card>
  );
}
