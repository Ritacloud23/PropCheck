import Link from "next/link";

import { buttonClass } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60dvh] max-w-md flex-col items-center justify-center px-4 text-center">
      <p className="text-sm font-semibold text-brand-700">404</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">We couldn&apos;t find that page</h1>
      <p className="mt-2 text-slate-600">The listing may have been removed, or the link is incorrect.</p>
      <div className="mt-6 flex gap-2">
        <Link href="/properties" className={buttonClass("primary", "md")}>
          Browse properties
        </Link>
        <Link href="/" className={buttonClass("secondary", "md")}>
          Home
        </Link>
      </div>
    </main>
  );
}
