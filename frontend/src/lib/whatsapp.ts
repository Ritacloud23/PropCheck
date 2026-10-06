import { toInternationalDigits } from "./format";

/** https://wa.me/2348031234567?text=... — null when the number is not a valid Nigerian mobile. */
export function waLink(number: string | null | undefined, text?: string): string | null {
  const intl = toInternationalDigits(number);
  if (!intl) return null;
  return text ? `https://wa.me/${intl}?text=${encodeURIComponent(text)}` : `https://wa.me/${intl}`;
}

export function waShareLink(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export function enquiryMessage(propertyTitle: string, url: string): string {
  return `Hello, I found "${propertyTitle}" on PropCheck Nigeria (${url}). Is it still available? I'd like to book an inspection.`;
}
