import Link from "next/link";

import { humanize } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Link-based filter tabs (?status=...). The first option is the default (no param). */
export function StatusTabs({ basePath, options, current }: { basePath: string; options: string[]; current?: string }) {
  return (
    <div className="-mx-4 mb-5 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <div className="flex gap-1.5">
        {options.map((o, i) => {
          const active = (current ?? options[0]) === o;
          return (
            <Link
              key={o}
              href={i === 0 ? basePath : `${basePath}?status=${o}`}
              className={cn(
                "whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium ring-1",
                active ? "bg-slate-900 text-white ring-slate-900" : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50",
              )}
            >
              {o === "WAITING" ? "Waiting" : humanize(o)}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
