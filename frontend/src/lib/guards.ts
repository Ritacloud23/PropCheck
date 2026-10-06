import "server-only";

import { redirect } from "next/navigation";

import { getCurrentUser } from "./server-api";
import type { Role, User } from "./types";

const HOME: Record<Role, string> = {
  RENTER: "/dashboard/renter",
  AGENT: "/dashboard/agent",
  LANDLORD: "/dashboard/agent",
  REVIEWER: "/dashboard/reviewer",
  ADMIN: "/dashboard/reviewer",
};

export function dashboardHome(role: Role): string {
  return HOME[role];
}

/** Server-side role gate for a dashboard section. The API enforces the same rules on every call. */
export async function requireRole(...roles: Role[]): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (!roles.includes(user.role)) redirect(HOME[user.role]);
  return user;
}
