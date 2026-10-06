import type { Metadata } from "next";

import { LoginForm } from "../auth-forms";

export const metadata: Metadata = { title: "Log in" };

export default async function LoginPage(props: PageProps<"/login">) {
  const { next } = await props.searchParams;
  return (
    <>
      <LoginForm next={typeof next === "string" ? next : undefined} />
      {process.env.NODE_ENV !== "production" && (
        <p className="mt-4 text-center text-xs text-slate-500">
          Demo accounts (password <code>PropCheck2026</code>): renter@, agent@, landlord@, reviewer@, admin@propcheck.ng
        </p>
      )}
    </>
  );
}
