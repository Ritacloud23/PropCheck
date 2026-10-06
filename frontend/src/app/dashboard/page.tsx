import { redirect } from "next/navigation";

import { dashboardHome } from "@/lib/guards";
import { getCurrentUser } from "@/lib/server-api";

export default async function DashboardIndex() {
  const user = await getCurrentUser();
  redirect(user ? dashboardHome(user.role) : "/login");
}
