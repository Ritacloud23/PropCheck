import { Check } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader, buttonClass } from "@/components/ui";

export const metadata: Metadata = { title: "Pricing" };

const PLANS = [
  {
    name: "Renters",
    price: "Free",
    note: "Always",
    features: ["Search all listings", "Read every verification report", "Book inspections", "Get matched with a verified agent"],
    cta: { href: "/register?role=RENTER", label: "Create renter account" },
  },
  {
    name: "Agent verification",
    price: "Free during pilot",
    note: "Planned: ₦15,000 / year",
    features: ["Identity & business review", "Verified Agent badge for 12 months", "Directory listing", "Matched renter requests"],
    cta: { href: "/register?role=AGENT", label: "Apply as an agent" },
    highlight: true,
  },
  {
    name: "Property verification",
    price: "Free during pilot",
    note: "Planned: ₦10,000 per listing",
    features: ["Authority & documents review", "Physical inspection", "Public report with reference number", "Valid for up to 6 months"],
    cta: { href: "/register?role=LANDLORD", label: "List a property" },
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <PageHeader
        title="Pricing"
        description="Renters never pay PropCheck. Agents and landlords pay for verification after the pilot — never for a better result."
      />
      <div className="grid gap-5 md:grid-cols-3">
        {PLANS.map((p) => (
          <div
            key={p.name}
            className={`flex flex-col rounded-2xl bg-white p-6 ring-1 ${p.highlight ? "ring-2 ring-brand-600" : "ring-slate-200"}`}
          >
            <p className="font-semibold text-slate-900">{p.name}</p>
            <p className="mt-3 text-3xl font-extrabold text-slate-900">{p.price}</p>
            <p className="text-sm text-slate-500">{p.note}</p>
            <ul className="mt-6 flex-1 space-y-2 text-sm text-slate-700">
              {p.features.map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="size-4 shrink-0 text-brand-600" aria-hidden /> {f}
                </li>
              ))}
            </ul>
            <Link href={p.cta.href} className={buttonClass(p.highlight ? "primary" : "secondary", "md", "mt-6")}>
              {p.cta.label}
            </Link>
          </div>
        ))}
      </div>
      <p className="mt-8 text-sm text-slate-600">
        Paying for verification never guarantees approval. Reviewers can reject or suspend regardless of payment, and every
        decision is recorded in an audit log. Planned prices are indicative and may change.
      </p>
    </div>
  );
}
