const nairaFormatter = new Intl.NumberFormat("en-NG", {
  style: "currency",
  currency: "NGN",
  maximumFractionDigits: 0,
});

/** ₦2,500,000 */
export function formatNaira(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  return nairaFormatter.format(amount).replace("NGN", "₦").replace(/\s/g, "");
}

/** Compact form for cards and filters: ₦2.5m, ₦850k */
export function formatNairaShort(amount: number): string {
  if (amount >= 1_000_000) return `₦${+(amount / 1_000_000).toFixed(1)}m`;
  if (amount >= 1_000) return `₦${Math.round(amount / 1_000)}k`;
  return `₦${amount}`;
}

/** Normalise a Nigerian mobile number to digits-only international form (2348031234567), or null. */
export function toInternationalDigits(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const digits = raw.replace(/[^\d]/g, "");
  const m = digits.match(/^(?:234|0)?([789][01]\d{8})$/);
  return m ? `234${m[1]}` : null;
}

/** +234 803 123 4567 */
export function formatNgPhone(raw: string | null | undefined): string {
  const intl = toInternationalDigits(raw);
  if (!intl) return raw ?? "";
  const local = intl.slice(3);
  return `+234 ${local.slice(0, 3)} ${local.slice(3, 6)} ${local.slice(6)}`;
}

export function isValidNgPhone(raw: string): boolean {
  return toInternationalDigits(raw) !== null;
}

// Always show Nigerian time (WAT), whatever the server or browser timezone is.
const TZ = "Africa/Lagos";
const dateFmt = new Intl.DateTimeFormat("en-NG", { timeZone: TZ, day: "numeric", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-NG", {
  timeZone: TZ,
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function formatDate(iso: string | null | undefined): string {
  return iso ? dateFmt.format(new Date(iso)) : "—";
}

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTimeFmt.format(new Date(iso)) : "—";
}

/** "SELF_CONTAINED" -> "Self contained" */
export function humanize(value: string | null | undefined): string {
  if (!value) return "";
  const s = value.replace(/_/g, " ").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const PROPERTY_TYPE_LABELS: Record<string, string> = {
  SELF_CONTAINED: "Self-contained",
  MINI_FLAT: "Mini flat",
  FLAT: "Flat / apartment",
  DUPLEX: "Duplex",
  TERRACE: "Terrace",
  BUNGALOW: "Bungalow",
  ROOM: "Room",
  SHOP: "Shop",
  OFFICE: "Office",
  LAND: "Land",
};

export function propertyTypeLabel(t: string): string {
  return PROPERTY_TYPE_LABELS[t] ?? humanize(t);
}

export function stateLabel(state: string): string {
  return state === "FCT" ? "Abuja (FCT)" : state;
}

/** "Lekki, Lagos" — the most specific place name we have, then the state. */
export function placeLabel(p: { area?: string | null; city: string; state: string }): string {
  const local = p.area && p.area !== p.city ? `${p.area}, ${p.city}` : p.city;
  return local === p.state ? local : `${local}, ${stateLabel(p.state)}`;
}

/** Under 1 km: metres (nearest 10 m). 1 km or more: kilometres to one decimal place. */
export function formatDistance(km: number): string {
  if (km < 1) {
    const metres = Math.max(10, Math.round((km * 1000) / 10) * 10);
    return metres >= 1000 ? "1.0 km" : `${metres} m`;
  }
  return `${km.toFixed(1)} km`;
}

/** Google Maps directions (works in the app on phones); starts from the property when given. */
export function directionsUrl(to: { latitude: number; longitude: number }, from?: { latitude: number; longitude: number } | null): string {
  const params = new URLSearchParams({ api: "1", destination: `${to.latitude},${to.longitude}` });
  if (from) params.set("origin", `${from.latitude},${from.longitude}`);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export const PLACE_CATEGORY_LABELS: Record<string, { one: string; many: string }> = {
  MARKET: { one: "Market", many: "Markets" },
  RESTAURANT: { one: "Restaurant", many: "Restaurants" },
  CHURCH: { one: "Church", many: "Churches" },
  CLUB: { one: "Club", many: "Clubs" },
};
