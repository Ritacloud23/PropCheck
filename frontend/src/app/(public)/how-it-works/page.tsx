import type { Metadata } from "next";
import Link from "next/link";

import { Disclaimer, SafetyWarning } from "@/components/disclaimer";
import { PageHeader, buttonClass } from "@/components/ui";
import { serverApi } from "@/lib/server-api";
import type { ReferenceData } from "@/lib/types";

export const metadata: Metadata = {
  title: "How verification works",
  description: "What PropCheck checks for agents and properties, what it doesn't, and how long a verification lasts.",
};

const STEPS = [
  ["Agent submits evidence", "Government ID and, where available, business registration. Files are stored privately."],
  ["Reviewer checks the agent", "A PropCheck reviewer compares the documents with the profile. The reviewer can never be the agent."],
  ["Agent lists a property", "With photos, the full fee breakdown and supporting documents such as an authority letter."],
  ["Reviewer inspects", "Location visited, photos compared, owner or manager contacted, fees confirmed — each recorded on a checklist."],
  ["Report published", "A dated report with a reference number, an expiry date, and a list of what was not checked."],
];

export default async function HowItWorksPage() {
  const reference = await serverApi<ReferenceData>("/api/reference", { auth: false }).catch(() => null);
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <PageHeader
        title="How verification works"
        description="Two independent checks — one for the agent, one for each property — done by people, recorded in an audit log, and published with their limits."
      />

      <ol className="space-y-4">
        {STEPS.map(([title, body], i) => (
          <li key={title} className="flex gap-4 rounded-xl bg-white p-5 ring-1 ring-slate-200">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-600 font-bold text-white">{i + 1}</span>
            <div>
              <p className="font-semibold text-slate-900">{title}</p>
              <p className="mt-1 text-sm text-slate-600">{body}</p>
            </div>
          </li>
        ))}
      </ol>

      {reference && (
        <section className="mt-10">
          <h2 className="text-xl font-bold text-slate-900">The property checklist</h2>
          <p className="mt-1 text-sm text-slate-600">
            A property is only marked verified when every item is passed or not applicable, and the core items (identity,
            authority to market, location, fees, availability) are passed.
          </p>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {reference.checks.map((c) => (
              <li key={c.check_type} className="rounded-lg bg-white px-4 py-3 text-sm ring-1 ring-slate-200">
                {c.label}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-10 grid gap-5 md:grid-cols-2">
        <div className="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="font-semibold text-slate-900">Verifications expire</h2>
          <p className="mt-2 text-sm text-slate-600">
            Property verifications last up to 6 months and agent verifications up to 12 months. If an agent changes the
            address, rent or fees after verification, the listing automatically shows as expired until it is re-checked.
          </p>
        </div>
        <div className="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="font-semibold text-slate-900">What we don&apos;t do</h2>
          <p className="mt-2 text-sm text-slate-600">
            We don&apos;t carry out land-registry or title searches, give legal advice, survey buildings or hold your rent in
            escrow. Use a lawyer for title questions on any long-term commitment.
          </p>
        </div>
      </section>

      <SafetyWarning className="mt-8" />
      <Disclaimer className="mt-4" />
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/properties?verified_only=true" className={buttonClass("primary", "lg")}>
          Browse verified properties
        </Link>
        <Link href="/register?role=AGENT" className={buttonClass("secondary", "lg")}>
          Get verified as an agent
        </Link>
      </div>
    </div>
  );
}
