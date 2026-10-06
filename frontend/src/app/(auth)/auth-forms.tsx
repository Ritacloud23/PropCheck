"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Alert, Button, Card, Field, Input } from "@/components/ui";
import { errorMessage, post } from "@/lib/api";
import { clean, loginSchema, registerSchema, type LoginInput, type RegisterInput } from "@/lib/schemas";
import type { User } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Only allow same-site relative redirects (no open redirect via ?next=). */
export function safeNext(next: string | undefined, fallback = "/dashboard"): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

export function LoginForm({ next }: { next?: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<LoginInput>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    try {
      await post<{ user: User }>("/api/auth/login", data);
      router.push(safeNext(next));
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <Card className="p-6 sm:p-8">
      <h1 className="text-2xl font-bold text-slate-900">Log in</h1>
      <p className="mt-1 text-sm text-slate-600">Welcome back to PropCheck.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Field label="Email" htmlFor="email" error={formState.errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
        </Field>
        <Field label="Password" htmlFor="password" error={formState.errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
        </Field>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button type="submit" loading={formState.isSubmitting} className="w-full">
          Log in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        New to PropCheck?{" "}
        <Link href="/register" className="font-semibold text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
    </Card>
  );
}

const ROLES = [
  { value: "RENTER", title: "I'm looking for a home", body: "Search, book inspections, get matched with an agent." },
  { value: "AGENT", title: "I'm an agent", body: "Get verified, list properties, receive matched renters." },
  { value: "LANDLORD", title: "I'm a landlord", body: "List your own property and get it verified." },
] as const;

export function RegisterForm({ defaultRole }: { defaultRole?: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const initialRole = ROLES.some((r) => r.value === defaultRole) ? (defaultRole as RegisterInput["role"]) : "RENTER";
  const { register, handleSubmit, formState, control } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: initialRole },
  });
  const role = useWatch({ control, name: "role" });

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    try {
      await post<{ user: User }>("/api/auth/register", clean(data));
      router.push({ RENTER: "/dashboard/renter", AGENT: "/dashboard/agent/profile", LANDLORD: "/dashboard/agent" }[data.role]);
      router.refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <Card className="p-6 sm:p-8">
      <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <fieldset className="space-y-2">
          <legend className="mb-1 text-sm font-medium text-slate-800">I am…</legend>
          {ROLES.map((r) => (
            <label
              key={r.value}
              className={cn(
                "flex cursor-pointer gap-3 rounded-xl border p-3 text-sm",
                role === r.value ? "border-brand-600 bg-brand-50" : "border-slate-200 hover:border-slate-300",
              )}
            >
              <input type="radio" value={r.value} {...register("role")} className="mt-1 accent-brand-600" />
              <span>
                <span className="block font-semibold text-slate-900">{r.title}</span>
                <span className="text-slate-600">{r.body}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <Field label="Full name" htmlFor="full_name" error={formState.errors.full_name?.message}>
          <Input id="full_name" autoComplete="name" {...register("full_name")} />
        </Field>
        <Field label="Email" htmlFor="email" error={formState.errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
        </Field>
        <Field label="Phone (optional)" htmlFor="phone" error={formState.errors.phone?.message} hint="Nigerian mobile, e.g. 0803 123 4567">
          <Input id="phone" type="tel" inputMode="tel" autoComplete="tel" {...register("phone")} />
        </Field>
        <Field label="Password" htmlFor="password" error={formState.errors.password?.message} hint="At least 8 characters with a letter and a number">
          <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
        </Field>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button type="submit" loading={formState.isSubmitting} className="w-full">
          Create account
        </Button>
        <p className="text-xs text-slate-500">
          Reviewer accounts are created by PropCheck staff and cannot be self-registered.
        </p>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </Card>
  );
}
