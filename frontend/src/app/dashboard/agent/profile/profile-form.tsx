"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, Button, Card, CardHeader, Checkbox, Field, Input, Textarea } from "@/components/ui";
import { api, errorMessage, post } from "@/lib/api";
import { humanize, propertyTypeLabel, stateLabel } from "@/lib/format";
import { agentProfileSchema, clean, type AgentProfileInput } from "@/lib/schemas";
import type { AgentPrivate, ReferenceData } from "@/lib/types";

function splitList(v: string | undefined): string[] {
  return (v ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function ProfileForm({ profile, reference }: { profile: AgentPrivate | null; reference: ReferenceData }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const { register, handleSubmit, formState } = useForm<AgentProfileInput>({
    resolver: zodResolver(agentProfileSchema),
    defaultValues: {
      agency_name: profile?.agency_name ?? "",
      bio: profile?.bio ?? "",
      phone_number: profile?.private_phone_number ?? "",
      whatsapp_number: profile?.private_whatsapp_number ?? "",
      email: profile?.private_email ?? "",
      states_covered: profile?.states_covered ?? ["Lagos"],
      cities_covered: profile?.cities_covered.join(", ") ?? "",
      property_types: profile?.property_types ?? [],
      service_types: profile?.service_types ?? ["RENTAL"],
      budget_min: profile?.budget_min ?? "",
      budget_max: profile?.budget_max ?? "",
      years_experience: profile?.years_experience ?? 0,
      display_phone_publicly: profile?.display_phone_publicly ?? false,
      display_email_publicly: profile?.display_email_publicly ?? false,
    },
  });
  const e = formState.errors;

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    setSaved(false);
    const body = clean({ ...data, cities_covered: splitList(data.cities_covered) });
    try {
      await api(`/api/agents/profile`, { method: profile ? "PATCH" : "POST", body });
      setSaved(true);
      router.refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  });

  return (
    <Card>
      <CardHeader title={profile ? "Public profile" : "Create your agent profile"} description="Shown in the Verified Agent directory." />
      <form onSubmit={onSubmit} className="space-y-5 p-5" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Agency / business name" htmlFor="agency">
            <Input id="agency" {...register("agency_name")} />
          </Field>
          <Field label="Years of experience" htmlFor="years" error={e.years_experience?.message}>
            <Input id="years" type="number" min={0} max={60} {...register("years_experience")} />
          </Field>
          <Field label="Phone" htmlFor="pphone" error={e.phone_number?.message}>
            <Input id="pphone" type="tel" inputMode="tel" {...register("phone_number")} />
          </Field>
          <Field label="WhatsApp (if different)" htmlFor="pwa" error={e.whatsapp_number?.message}>
            <Input id="pwa" type="tel" inputMode="tel" {...register("whatsapp_number")} />
          </Field>
          <Field label="Business email" htmlFor="pemail" error={e.email?.message}>
            <Input id="pemail" type="email" {...register("email")} />
          </Field>
        </div>
        <Field label="About you" htmlFor="bio" hint="Areas you know well, how you work, what renters can expect.">
          <Textarea id="bio" rows={4} {...register("bio")} />
        </Field>

        <fieldset>
          <legend className="mb-2 text-sm font-medium text-slate-800">States covered</legend>
          <div className="grid max-h-48 grid-cols-2 gap-1.5 overflow-y-auto rounded-xl border border-slate-200 p-3 sm:grid-cols-3">
            {reference.states.map((s) => (
              <label key={s} className="flex items-center gap-2 text-sm">
                <input type="checkbox" value={s} {...register("states_covered")} className="accent-brand-600" /> {stateLabel(s)}
              </label>
            ))}
          </div>
          {e.states_covered && <p className="mt-1 text-xs font-medium text-red-700">{e.states_covered.message}</p>}
        </fieldset>
        <Field label="Areas / cities covered" htmlFor="cities" hint="Comma-separated, e.g. Lekki, Ajah, Victoria Island">
          <Input id="cities" {...register("cities_covered")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-800">Property types</legend>
            <div className="grid grid-cols-2 gap-1.5">
              {reference.property_types.map((t) => (
                <label key={t} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" value={t} {...register("property_types")} className="accent-brand-600" /> {propertyTypeLabel(t)}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-800">Services</legend>
            <div className="grid gap-1.5">
              {reference.service_types.map((t) => (
                <label key={t} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" value={t} {...register("service_types")} className="accent-brand-600" /> {humanize(t)}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Typical budget from (₦/year)" htmlFor="bmin" error={e.budget_min?.message}>
            <Input id="bmin" type="number" min={0} step={50000} {...register("budget_min")} />
          </Field>
          <Field label="Typical budget to (₦/year)" htmlFor="bmax" error={e.budget_max?.message}>
            <Input id="bmax" type="number" min={0} step={50000} {...register("budget_max")} />
          </Field>
        </div>
        <div className="space-y-2 rounded-xl bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-800">Privacy</p>
          <Checkbox {...register("display_phone_publicly")} label="Show my phone and WhatsApp number publicly on my profile and listings" />
          <Checkbox {...register("display_email_publicly")} label="Show my business email publicly" />
          <p className="text-xs text-slate-500">
            If unticked, renters reach you only through PropCheck matching or inspection bookings.
          </p>
        </div>
        {error && <Alert tone="danger">{error}</Alert>}
        {saved && <Alert tone="success">Profile saved.</Alert>}
        <Button type="submit" loading={formState.isSubmitting}>
          {profile ? "Save changes" : "Create profile"}
        </Button>
      </form>
    </Card>
  );
}

export function PhotoUpload() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const upload = async (file: File | undefined) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true);
    setError(null);
    try {
      await post("/api/agents/profile/photo", fd);
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <label className="text-sm font-medium text-brand-700 hover:underline">
        {busy ? "Uploading…" : "Change photo"}
        <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => upload(e.target.files?.[0])} />
      </label>
      {error && <p className="text-xs text-red-700">{error}</p>}
    </div>
  );
}

export function VerificationUpload() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (ev: React.FormEvent<HTMLFormElement>) => {
    ev.preventDefault();
    const fd = new FormData(ev.currentTarget);
    const id = fd.get("identity_document");
    if (!(id instanceof File) || id.size === 0) {
      setError("Please attach a government ID.");
      return;
    }
    const biz = fd.get("business_document");
    if (biz instanceof File && biz.size === 0) fd.delete("business_document");
    setBusy(true);
    setError(null);
    try {
      await post("/api/agents/profile/verification", fd);
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Government ID (NIN slip, passport, driver's licence or voter's card)" htmlFor="idoc" hint="PDF, JPG, PNG or WEBP · max 10 MB · stored privately">
        <Input id="idoc" name="identity_document" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="py-2" />
      </Field>
      <Field label="Business registration (CAC) — optional" htmlFor="bdoc">
        <Input id="bdoc" name="business_document" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" className="py-2" />
      </Field>
      <Field label="Notes for the reviewer (optional)" htmlFor="enotes">
        <Textarea id="enotes" name="evidence_notes" maxLength={2000} />
      </Field>
      {error && <Alert tone="danger">{error}</Alert>}
      <Button type="submit" loading={busy}>
        Submit for verification
      </Button>
    </form>
  );
}
