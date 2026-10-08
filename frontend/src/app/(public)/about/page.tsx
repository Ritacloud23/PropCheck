import type { Metadata } from "next";
import Link from "next/link";

import { Disclaimer } from "@/components/disclaimer";
import { PageHeader, buttonClass } from "@/components/ui";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <PageHeader title="About PropCheck Nigeria" />
      <div className="space-y-5 text-slate-700">
        <p>
          Renting in Lagos, Port Harcourt, Enugu, Awka or Owerri too often means paying a year&apos;s rent, plus agency, legal and caution fees, to
          someone you met online - before you can be sure they are allowed to let the property, or that it exists as
          advertised.
        </p>
        <p>
          PropCheck is a verification layer for that moment. We check agents&apos; identities and, separately, individual
          listings: the agent&apos;s authority to market the property, its location and photos, and the full move-in cost.
          Then we publish exactly what was checked, when, and what was not.
        </p>
        <p>
          We are deliberately honest about limits. A PropCheck badge is not a title search or legal opinion, and our
          reservation feature is a test-mode demonstration, not escrow.
        </p>
        <h2 className="pt-4 text-xl font-bold text-slate-900">Principles</h2>
        <ul className="list-disc space-y-2 pl-5">
          <li>People review evidence; software only helps them.</li>
          <li>Agent verification and property verification are never mixed up.</li>
          <li>Contact details are shown only with the agent&apos;s consent.</li>
          <li>Private documents stay private and are only seen by reviewers.</li>
          <li>Every approval, rejection and suspension is recorded in an audit log.</li>
        </ul>
      </div>
      <Disclaimer className="mt-8" />
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/how-it-works" className={buttonClass("primary", "md")}>
          How verification works
        </Link>
        <Link href="/report-problem" className={buttonClass("secondary", "md")}>
          Report a problem
        </Link>
      </div>
    </div>
  );
}
