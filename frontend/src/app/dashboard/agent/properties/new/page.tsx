import { PageHeader } from "@/components/ui";
import { getReference } from "@/lib/server-api";

import { PropertyForm } from "../property-form";

export default async function NewPropertyPage() {
  const reference = await getReference();
  return (
    <>
      <PageHeader title="Add a listing" description="After saving you can add photos, documents and inspection times." />
      <PropertyForm reference={reference} />
    </>
  );
}
