import { describe, expect, it } from "vitest";

import { formatNaira, formatNairaShort, formatNgPhone, isValidNgPhone, toInternationalDigits } from "@/lib/format";
import { enquiryMessage, waLink, waShareLink } from "@/lib/whatsapp";

describe("formatNaira", () => {
  it("formats whole naira with the ₦ sign and thousands separators", () => {
    expect(formatNaira(2_500_000)).toBe("₦2,500,000");
    expect(formatNaira(0)).toBe("₦0");
    expect(formatNaira(950)).toBe("₦950");
  });
  it("shows a dash for missing values", () => {
    expect(formatNaira(null)).toBe("—");
    expect(formatNaira(undefined)).toBe("—");
  });
  it("has a compact form", () => {
    expect(formatNairaShort(2_500_000)).toBe("₦2.5m");
    expect(formatNairaShort(850_000)).toBe("₦850k");
  });
});

describe("Nigerian phone numbers", () => {
  it.each([
    ["08031234567", "+234 803 123 4567"],
    ["0803 123 4567", "+234 803 123 4567"],
    ["+2348031234567", "+234 803 123 4567"],
    ["2349051234567", "+234 905 123 4567"],
    ["(0701) 234-5678", "+234 701 234 5678"],
  ])("formats %s", (raw, expected) => {
    expect(formatNgPhone(raw)).toBe(expected);
  });
  it("rejects invalid numbers", () => {
    expect(isValidNgPhone("12345")).toBe(false);
    expect(isValidNgPhone("06031234567")).toBe(false);
    expect(toInternationalDigits("")).toBeNull();
    expect(formatNgPhone("12345")).toBe("12345");
  });
});

describe("WhatsApp links", () => {
  it("uses the international number without +", () => {
    expect(waLink("0803 123 4567")).toBe("https://wa.me/2348031234567");
  });
  it("URL-encodes the message", () => {
    const text = 'Hi! Is "2-bed flat" in Lekki & Ajah available? 50% off?';
    const link = waLink("+2348031234567", text)!;
    expect(link).toBe(
      "https://wa.me/2348031234567?text=Hi!%20Is%20%222-bed%20flat%22%20in%20Lekki%20%26%20Ajah%20available%3F%2050%25%20off%3F",
    );
    expect(decodeURIComponent(link.split("?text=")[1])).toBe(text);
  });
  it("returns null for missing or invalid numbers", () => {
    expect(waLink(null, "hi")).toBeNull();
    expect(waLink("123", "hi")).toBeNull();
  });
  it("builds share links and enquiry text", () => {
    expect(waShareLink("a b&c")).toBe("https://wa.me/?text=a%20b%26c");
    expect(enquiryMessage("Flat", "http://x/p")).toContain('"Flat"');
  });
});
