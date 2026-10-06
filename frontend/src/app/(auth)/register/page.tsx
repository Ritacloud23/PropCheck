import type { Metadata } from "next";

import { RegisterForm } from "../auth-forms";

export const metadata: Metadata = { title: "Create an account" };

export default async function RegisterPage(props: PageProps<"/register">) {
  const { role } = await props.searchParams;
  return <RegisterForm defaultRole={typeof role === "string" ? role : undefined} />;
}
