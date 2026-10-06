import Link from "next/link";

import { DISCLAIMER } from "./disclaimer";
import { Logo } from "./site-header";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo />
          <p className="mt-3 max-w-md text-sm text-slate-600">Verify the property and agent before you pay rent.</p>
          <p className="mt-4 max-w-xl text-xs leading-relaxed text-slate-500">{DISCLAIMER}</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Renters</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li><Link href="/properties?verified_only=true" className="hover:text-brand-700">Verified properties</Link></li>
            <li><Link href="/agents?verified_only=true" className="hover:text-brand-700">Verified agents</Link></li>
            <li><Link href="/find-an-agent" className="hover:text-brand-700">Help me find a house</Link></li>
            <li><Link href="/report-problem" className="hover:text-brand-700">Report a problem</Link></li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Company</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li><Link href="/about" className="hover:text-brand-700">About</Link></li>
            <li><Link href="/how-it-works" className="hover:text-brand-700">How verification works</Link></li>
            <li><Link href="/pricing" className="hover:text-brand-700">Pricing for agents</Link></li>
            <li><Link href="/register?role=AGENT" className="hover:text-brand-700">List as an agent</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-slate-100 py-4 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} PropCheck Nigeria · MVP demo. Payments run in Paystack test mode only.
      </div>
    </footer>
  );
}
