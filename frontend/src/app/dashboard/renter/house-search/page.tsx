import Link from "next/link";

import { EmptyState, PageHeader, buttonClass } from "@/components/ui";
import { serverApi } from "@/lib/server-api";
import type { HouseSearchRequest } from "@/lib/types";

import { RequestCard } from "./request-card";

export default async function RenterRequests() {
  const requests = await serverApi<HouseSearchRequest[]>("/api/house-search-requests");
  return (
    <>
      <PageHeader
        title="House-search requests"
        description="Each request is shared only with the one verified agent PropCheck assigns."
        action={
          <Link href="/find-an-agent" className={buttonClass("primary", "md")}>
            New request
          </Link>
        }
      />
      {!requests.length ? (
        <EmptyState title="No requests yet" action={<Link href="/find-an-agent" className={buttonClass("primary", "md")}>Ask for help</Link>}>
          Tell us what you&apos;re looking for and we&apos;ll match you with a verified agent.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {requests.map((r) => (
            <RequestCard key={r.id} request={r} linkTitle />
          ))}
        </div>
      )}
    </>
  );
}
