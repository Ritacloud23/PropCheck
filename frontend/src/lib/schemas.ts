// Zod schemas mirror the backend's Pydantic validation, so users see the same rules before submitting.
import { z } from "zod";

import { isValidNgPhone } from "./format";

const phone = z
  .string()
  .trim()
  .refine(isValidNgPhone, "Enter a valid Nigerian mobile number, e.g. 0803 123 4567.");
const optionalPhone = z
  .string()
  .trim()
  .refine((v) => v === "" || isValidNgPhone(v), "Enter a valid Nigerian mobile number.")
  .optional();
const naira = z.coerce.number<string | number>().int("Whole naira only").min(0, "Cannot be negative");

export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name").max(120),
  email: z.email("Enter a valid email address"),
  phone: optionalPhone,
  password: z
    .string()
    .min(8, "At least 8 characters")
    .regex(/[A-Za-z]/, "Include at least one letter")
    .regex(/\d/, "Include at least one number"),
  role: z.enum(["RENTER", "AGENT", "LANDLORD"]),
});

export const houseSearchSchema = z
  .object({
    name: z.string().trim().min(2, "Enter your name").max(120),
    phone,
    whatsapp_number: optionalPhone,
    email: z.union([z.email("Enter a valid email"), z.literal("")]).optional(),
    state: z.string().min(1, "Choose a state"),
    city: z.string().trim().min(2, "Choose a city"),
    area: z.string().max(80).optional(),
    property_type: z.string().min(1, "Choose a property type"),
    bedrooms: z.coerce.number<string | number>().int().min(0).max(20),
    budget_min: naira,
    budget_max: naira.refine((v) => v > 0, "Enter your maximum budget"),
    purpose: z.enum(["RENT", "PURCHASE"]),
    preferred_move_in_date: z.string().optional(),
    furnished_preference: z.enum(["FURNISHED", "UNFURNISHED", "EITHER"]),
    description: z.string().max(2000).optional(),
    consent_to_share: z.boolean().refine((v) => v, "We need your consent to share this request with an agent."),
  })
  .refine((d) => d.budget_min <= d.budget_max, {
    path: ["budget_min"],
    message: "Minimum budget cannot be more than maximum budget.",
  });

export const propertySchema = z.object({
  title: z.string().trim().min(5, "At least 5 characters").max(160),
  description: z.string().max(5000).optional(),
  address: z.string().trim().min(5, "Enter the street address").max(300),
  landmark: z.string().max(200).optional(),
  state: z.string().min(1, "Choose a state"),
  city: z.string().trim().min(2, "Choose a city").max(80),
  area: z.string().max(80).optional(),
  local_government_area: z.string().max(80).optional(),
  latitude: z.union([z.literal(""), z.coerce.number<string | number>().min(4).max(14)]).optional(),
  longitude: z.union([z.literal(""), z.coerce.number<string | number>().min(2.5).max(15)]).optional(),
  property_type: z.string().min(1, "Choose a type"),
  bedrooms: z.coerce.number<string | number>().int().min(0).max(20),
  bathrooms: z.coerce.number<string | number>().int().min(0).max(20),
  furnished: z.boolean(),
  rent_amount: naira.refine((v) => v > 0, "Enter the annual rent"),
  agency_fee: naira,
  legal_fee: naira,
  caution_fee: naira,
  other_fees: naira,
  other_fees_description: z.string().max(300).optional(),
});

export const agentProfileSchema = z
  .object({
    agency_name: z.string().max(160).optional(),
    bio: z.string().max(2000).optional(),
    phone_number: phone,
    whatsapp_number: optionalPhone,
    email: z.union([z.email("Enter a valid email"), z.literal("")]).optional(),
    states_covered: z.array(z.string()).min(1, "Choose at least one state"),
    cities_covered: z.string().optional(),
    property_types: z.array(z.string()),
    service_types: z.array(z.string()),
    budget_min: z.union([z.literal(""), naira]).optional(),
    budget_max: z.union([z.literal(""), naira]).optional(),
    years_experience: z.coerce.number<string | number>().int().min(0).max(60),
    display_phone_publicly: z.boolean(),
    display_email_publicly: z.boolean(),
  })
  .refine((d) => d.budget_min === "" || d.budget_max === "" || d.budget_min === undefined || d.budget_max === undefined || d.budget_min <= d.budget_max, {
    path: ["budget_min"],
    message: "Minimum cannot be more than maximum.",
  });

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type HouseSearchInput = z.input<typeof houseSearchSchema>;
export type PropertyInput = z.input<typeof propertySchema>;
export type AgentProfileInput = z.input<typeof agentProfileSchema>;

/** Turns "" into null and drops undefined, for JSON bodies sent to the API. */
export function clean<T extends Record<string, unknown>>(data: T): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    if (v === undefined) continue;
    out[k] = v === "" ? null : v;
  }
  return out;
}
