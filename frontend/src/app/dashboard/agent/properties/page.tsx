import Link from "next/link";

import { PropertyCard } from "@/components/property-card";
import { EmptyState, PageHeader, buttonClass } from "@/components/ui";
import { serverApi } from "@/lib/server-api";
import type { PropertyCard as PropertyCardT } from "@/lib/types";

export default async function MyProperties() {
  const properties = await serverApi<PropertyCardT[]>("/api/properties/mine");
  return (
    <>
      <PageHeader
        title="My listings"
        action={
          <Link href="/dashboard/agent/properties/new" className={buttonClass("primary", "md")}>
            Add a listing
          </Link>
        }
      />
      {!properties.length ? (
        <EmptyState
          title="No listings yet"
          action={<Link href="/dashboard/agent/properties/new" className={buttonClass("primary", "md")}>Add your first listing</Link>}
        >
          Add photos, the full fee breakdown and an authority letter, then submit it for verification.
        </EmptyState>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {properties.map((p) => (
            <PropertyCard key={p.id} property={p} href={`/dashboard/agent/properties/${p.id}`} />
          ))}
        </div>
      )}
    </>
  );
}
