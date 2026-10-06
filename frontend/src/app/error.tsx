"use client";

import { buttonClass } from "@/components/ui";

export default function ErrorPage({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <main className="mx-auto flex min-h-[60dvh] max-w-md flex-col items-center justify-center px-4 text-center">
      <h1 className="text-2xl font-bold text-slate-900">Something went wrong</h1>
      <p className="mt-2 text-slate-600">Please try again. If the problem continues, the service may be temporarily unavailable.</p>
      <button onClick={() => retry()} className={buttonClass("primary", "md", "mt-6")}>
        Try again
      </button>
    </main>
  );
}
