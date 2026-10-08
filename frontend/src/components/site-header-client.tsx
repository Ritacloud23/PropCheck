"use client";

import { LayoutDashboard, LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { post } from "@/lib/api";
import { humanize } from "@/lib/format";
import type { Role } from "@/lib/types";

import { buttonClass } from "./ui";

export function useLogout() {
  const router = useRouter();
  return async () => {
    await post("/api/auth/logout").catch(() => undefined);
    router.push("/");
    router.refresh();
  };
}

export function UserMenu({ name, role, dashboardHref }: { name: string; role: Role; dashboardHref: string }) {
  const logout = useLogout();
  return (
    <div className="hidden items-center gap-2 sm:flex">
      <Link href={dashboardHref} className={buttonClass("secondary", "sm")}>
        <LayoutDashboard className="size-4" aria-hidden />
        Dashboard
        <span className="max-w-32 truncate text-xs font-normal text-slate-500">
          · {name.split(" ")[0]}, {humanize(role)}
        </span>
      </Link>
      <button onClick={logout} className={buttonClass("ghost", "sm")} aria-label="Log out">
        <LogOut className="size-4" aria-hidden />
      </button>
    </div>
  );
}

export function MobileMenu({ nav, dashboardHref }: { nav: { href: string; label: string }[]; dashboardHref: string | null }) {
  const [open, setOpen] = useState(false);
  const logout = useLogout();

  return (
    <div className="lg:hidden">
      <button
        className={buttonClass("ghost", "sm")}
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <X className="size-5" /> : <Menu className="size-5" />}
      </button>
      {open && (
        <div
          className="absolute inset-x-0 top-16 border-b border-slate-200 bg-white px-4 pb-4 shadow-lg"
          // Close the sheet after any link or button inside it is used.
          onClick={(e) => (e.target as HTMLElement).closest("a,button") && setOpen(false)}
        >
          <nav className="flex flex-col py-2" aria-label="Mobile">
            {nav.map((n) => (
              <Link key={n.href} href={n.href} className="rounded-lg px-3 py-3 font-medium text-slate-800 hover:bg-slate-100">
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="grid grid-cols-2 gap-2 border-t border-slate-100 pt-3">
            {dashboardHref ? (
              <>
                <Link href={dashboardHref} className={buttonClass("primary", "md")}>
                  Dashboard
                </Link>
                <button onClick={logout} className={buttonClass("secondary", "md")}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className={buttonClass("secondary", "md")}>
                  Log in
                </Link>
                <Link href="/register" className={buttonClass("primary", "md")}>
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
