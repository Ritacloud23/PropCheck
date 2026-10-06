"use client";

import { SlidersHorizontal, X } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

import { buttonClass } from "./ui";

/**
 * Filters live in a plain GET <form>, so they work without JavaScript. On small screens the
 * form is shown in a bottom sheet behind a "Filters" button; on large screens it is a sidebar.
 */
export function FilterDrawer({
  action,
  activeCount,
  children,
}: {
  action: string;
  activeCount: number;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={buttonClass("secondary", "md", "w-full lg:hidden")}>
        <SlidersHorizontal className="size-4" aria-hidden />
        Filters{activeCount > 0 && ` (${activeCount})`}
      </button>
      {open && <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} aria-hidden />}
      <form
        action={action}
        method="get"
        className={cn(
          "space-y-4",
          "lg:static lg:block lg:rounded-xl lg:border lg:border-slate-200 lg:bg-white lg:p-5 lg:shadow-sm",
          open
            ? "fixed inset-x-0 bottom-0 z-50 max-h-[85dvh] overflow-y-auto rounded-t-2xl bg-white p-5 shadow-2xl"
            : "hidden",
        )}
        aria-label="Filters"
      >
        <div className="flex items-center justify-between lg:hidden">
          <p className="text-lg font-semibold">Filters</p>
          <button type="button" onClick={() => setOpen(false)} className={buttonClass("ghost", "sm")} aria-label="Close filters">
            <X className="size-5" />
          </button>
        </div>
        {children}
        <div className="sticky bottom-0 grid grid-cols-2 gap-2 bg-white pt-2">
          <Link href={action} className={buttonClass("secondary", "md")}>
            Clear
          </Link>
          <button type="submit" className={buttonClass("primary", "md")}>
            Apply
          </button>
        </div>
      </form>
    </>
  );
}
