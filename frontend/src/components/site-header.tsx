import { ShieldCheck } from "lucide-react";
import Link from "next/link";

import { dashboardHome } from "@/lib/guards";
import { getCurrentUser } from "@/lib/server-api";

import { MobileMenu, UserMenu } from "./site-header-client";
import { buttonClass } from "./ui";

export const NAV = [
  { href: "/properties", label: "Properties" },
  { href: "/agents", label: "Find an agent" },
  { href: "/nearby", label: "Nearby places" },
  { href: "/how-it-works", label: "How it works" },
  // No contact page yet; the house-search request form is how renters reach the team.
  { href: "/find-an-agent", label: "Get in touch" },
];

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-forest text-highlight">
        <ShieldCheck className="size-5" aria-hidden />
      </span>
      <span className="flex flex-col">
        <span className="text-lg font-extrabold leading-none tracking-tight text-deep">PropCheck</span>
        <span className="mt-1 text-xs font-medium leading-none text-muted">Nigeria&apos;s trusted home search</span>
      </span>
    </Link>
  );
}

export async function SiteHeader() {
  const user = await getCurrentUser();
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {user ? (
            <UserMenu name={user.full_name} role={user.role} dashboardHref={dashboardHome(user.role)} />
          ) : (
            <div className="hidden items-center gap-2 sm:flex">
              <Link href="/login" className={buttonClass("ghost", "sm")}>
                Log in
              </Link>
              <Link href="/register" className={buttonClass("primary", "sm")}>
                Sign up
              </Link>
            </div>
          )}
          <MobileMenu nav={NAV} dashboardHref={user ? dashboardHome(user.role) : null} />
        </div>
      </div>
    </header>
  );
}
