// Mirrors backend Pydantic schemas (backend/app/schemas). Keep in sync when the API changes.

export type Role = "RENTER" | "AGENT" | "LANDLORD" | "REVIEWER" | "ADMIN";

export type AgentVerificationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "IN_REVIEW"
  | "VERIFIED"
  | "REJECTED"
  | "SUSPENDED"
  | "EXPIRED";

export type CaseStatus = "DRAFT" | "SUBMITTED" | "IN_REVIEW" | "INSPECTION_BOOKED" | "VERIFIED" | "REJECTED" | "EXPIRED";
export type PropertyVerificationState = CaseStatus | "NOT_SUBMITTED";
export type CheckResult = "NOT_STARTED" | "PASSED" | "FAILED" | "NOT_APPLICABLE";
export type DocumentReviewStatus = "UPLOADED" | "REVIEWED" | "ACCEPTED" | "REJECTED";
export type AvailabilityStatus = "AVAILABLE" | "RESERVED" | "LET" | "UNAVAILABLE";
export type BookingStatus = "REQUESTED" | "CONFIRMED" | "DECLINED" | "COMPLETED" | "CANCELLED";
export type HouseSearchStatus = "SUBMITTED" | "MATCHING" | "ASSIGNED" | "CONTACTED" | "COMPLETED" | "CANCELLED";
export type ReservationStatus = "PENDING_PAYMENT" | "PENDING_RELEASE" | "RELEASED" | "REFUNDED" | "CANCELLED";
export type ReportStatus = "OPEN" | "IN_REVIEW" | "RESOLVED" | "REJECTED";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface AgentSummary {
  id: number;
  name: string;
  agency_name: string | null;
  profile_photo_url: string | null;
  verification_status: AgentVerificationStatus;
  is_verified: boolean;
  verification_expiry_date: string | null;
}

export interface AgentPublic {
  id: number;
  name: string;
  agency_name: string | null;
  bio: string;
  profile_photo_url: string | null;
  phone_number: string | null;
  whatsapp_number: string | null;
  email: string | null;
  contact_public: boolean;
  states_covered: string[];
  cities_covered: string[];
  lgas_covered: string[];
  property_types: string[];
  service_types: string[];
  budget_min: number | null;
  budget_max: number | null;
  years_experience: number;
  verification_status: AgentVerificationStatus;
  is_verified: boolean;
  verification_date: string | null;
  verification_expiry_date: string | null;
  active_listings: number;
  completed_connections: number;
  average_rating: number | null;
  total_reviews: number;
  complaint_status: "NO_OPEN_COMPLAINTS" | "COMPLAINT_UNDER_REVIEW" | "SUSPENDED";
  response_time_hours: number | null;
  joined_at: string;
}

export interface AgentApplication {
  id: number;
  status: AgentVerificationStatus;
  evidence_notes: string | null;
  submitted_at: string | null;
  verified_at: string | null;
  expires_at: string | null;
  rejection_reason: string | null;
  reviewer_notes: string | null;
  assigned_reviewer_id: number | null;
  has_identity_document: boolean;
  has_business_document: boolean;
  identity_document_link: string | null;
  business_document_link: string | null;
  created_at: string;
}

export interface AgentPrivate extends AgentPublic {
  user_id: number;
  private_phone_number: string;
  private_whatsapp_number: string | null;
  private_email: string | null;
  display_phone_publicly: boolean;
  display_email_publicly: boolean;
  latest_application: AgentApplication | null;
}

export interface ReviewerAgent extends AgentPrivate {
  account_email: string;
  open_reports: number;
  allowed_actions: string[];
}

export interface VerificationBadge {
  status: PropertyVerificationState;
  is_currently_verified: boolean;
  reference: string | null;
  verified_at: string | null;
  expires_at: string | null;
}

export interface PropertyCard {
  id: number;
  public_slug: string;
  title: string;
  state: string;
  city: string;
  local_government_area: string | null;
  area: string | null;
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  furnished: boolean;
  rent_amount: number;
  total_move_in_cost: number;
  availability_status: AvailabilityStatus;
  cover_photo_url: string | null;
  verification: VerificationBadge;
  agent: AgentSummary | null;
  created_at: string;
}

export interface Fees {
  rent_amount: number;
  agency_fee: number;
  legal_fee: number;
  caution_fee: number;
  other_fees: number;
  other_fees_description: string | null;
  total_move_in_cost: number;
}

export interface Media {
  id: number;
  media_type: string;
  url: string;
  caption: string | null;
  created_at: string;
}

export interface PropertyDocument {
  id: number;
  document_type: string;
  original_filename: string | null;
  review_status: DocumentReviewStatus;
  reviewer_notes: string | null;
  uploaded_at: string;
  reviewed_at: string | null;
  link: string | null;
}

export interface PropertyDetail extends PropertyCard {
  description: string;
  address: string;
  landmark: string | null;
  latitude: number | null;
  longitude: number | null;
  fees: Fees;
  media: Media[];
  agent_profile: AgentPublic | null;
  is_listed: boolean;
  share_url: string;
  can_manage: boolean;
  documents: PropertyDocument[] | null;
  owner_user_id: number | null;
  latest_case_id: number | null;
}

export interface TimelineEntry {
  action: string;
  from_status: string | null;
  to_status: string | null;
  at: string;
}

export interface VerificationReport {
  property_id: number;
  property_slug: string;
  property_title: string;
  status: PropertyVerificationState;
  is_currently_verified: boolean;
  verification_reference: string | null;
  submitted_at: string | null;
  inspection_date: string | null;
  verified_at: string | null;
  expires_at: string | null;
  reviewer_reference: string | null;
  checks: { check_type: string; label: string; result: CheckResult; evidence_note: string | null; completed_at: string | null }[];
  what_was_checked: string[];
  what_was_not_checked: string[];
  documents_reviewed: { document_type: string; review_status: DocumentReviewStatus; reviewed_at: string | null }[];
  limitations: string[];
  rejection_reason: string | null;
  timeline: TimelineEntry[];
  agent_verified: boolean;
  agent_note: string;
  disclaimer: string;
  payment_warning: string;
}

export interface PropertyRef {
  id: number;
  title: string;
  public_slug: string;
  state: string;
  city: string;
}

export interface CheckItem {
  id: number;
  check_type: string;
  label: string;
  result: CheckResult;
  evidence_note: string | null;
  document_url: string | null;
  completed_by: number | null;
  completed_at: string | null;
}

export interface VerificationCase {
  id: number;
  property: PropertyRef;
  status: CaseStatus;
  effective_status: CaseStatus;
  verification_reference: string;
  submitted_by: number;
  submitted_by_name: string | null;
  assigned_reviewer_id: number | null;
  submitted_at: string | null;
  inspection_booked_at: string | null;
  inspection_scheduled_for: string | null;
  inspected_at: string | null;
  verified_at: string | null;
  expires_at: string | null;
  rejection_reason: string | null;
  reviewer_notes: string | null;
  created_at: string;
  checks: CheckItem[];
  documents: PropertyDocument[];
  allowed_transitions: string[];
  listing_agent: AgentPublic | null;
}

export interface Slot {
  id: number;
  property_id: number;
  start_time: string;
  end_time: string;
  status: "OPEN" | "BOOKED" | "CANCELLED";
}

export interface Booking {
  id: number;
  property: PropertyRef;
  slot_id: number;
  start_time: string;
  end_time: string;
  status: BookingStatus;
  renter_note: string | null;
  landlord_note: string | null;
  created_at: string;
  confirmed_at: string | null;
  completed_at: string | null;
  renter_name: string | null;
  renter_phone: string | null;
  allowed_actions: BookingStatus[];
}

export interface Enquiry {
  id: number;
  house_search_request_id: number;
  agent_id: number;
  agent_name: string | null;
  message: string | null;
  status: "PENDING" | "RESPONDED" | "CLOSED";
  created_at: string;
  responded_at: string | null;
}

export interface HouseSearchRequest {
  id: number;
  renter_id: number;
  name: string;
  phone: string;
  whatsapp_number: string | null;
  email: string | null;
  state: string;
  city: string;
  local_government_area: string | null;
  area: string | null;
  property_type: string;
  bedrooms: number;
  budget_min: number;
  budget_max: number;
  purpose: "RENT" | "PURCHASE";
  preferred_move_in_date: string | null;
  furnished_preference: "FURNISHED" | "UNFURNISHED" | "EITHER";
  description: string | null;
  consent_to_share: boolean;
  status: HouseSearchStatus;
  assigned_agent_id: number | null;
  assigned_agent: AgentPublic | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  enquiries: Enquiry[];
  allowed_actions: HouseSearchStatus[];
}

export interface AgentEnquiry {
  id: number;
  status: Enquiry["status"];
  message: string | null;
  created_at: string;
  responded_at: string | null;
  request: HouseSearchRequest;
}

export interface Reservation {
  id: number;
  property: PropertyRef;
  renter_id: number;
  renter_name: string | null;
  amount: number;
  payment_reference: string | null;
  payment_provider: string | null;
  status: ReservationStatus;
  terms_version: string;
  terms: string[];
  created_at: string;
  paid_at: string | null;
  released_at: string | null;
  refunded_at: string | null;
  refund_requested_at: string | null;
  refund_request_reason: string | null;
  cancellation_reason: string | null;
  is_test_mode: boolean;
  allowed_actions: ReservationStatus[];
}

export interface Report {
  id: number;
  reporter_id: number;
  reporter_name: string | null;
  agent_id: number | null;
  agent_name: string | null;
  property: PropertyRef | null;
  reason: string;
  description: string;
  has_evidence: boolean;
  evidence_link: string | null;
  status: ReportStatus;
  reviewer_notes: string | null;
  resolution_reason: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface AuditEntry {
  id: number;
  actor_user_id: number | null;
  actor_name: string | null;
  entity_type: string;
  entity_id: number;
  action: string;
  from_status: string | null;
  to_status: string | null;
  reason: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface AreaRef {
  area: string;
  lga: string;
  latitude: number;
  longitude: number;
}

export interface CityRef {
  city: string;
  major: boolean;
  latitude: number;
  longitude: number;
  areas: AreaRef[];
}

export type PlaceCategory = "MARKET" | "RESTAURANT" | "CHURCH" | "CLUB";

export interface NearbyPlace {
  id: number;
  name: string;
  category: PlaceCategory;
  description: string | null;
  address: string | null;
  area: string | null;
  city: string;
  local_government_area: string | null;
  state: string;
  latitude: number;
  longitude: number;
  phone_number: string | null;
  website_url: string | null;
  opening_hours: string | null;
  distance_km: number;
  distance_m: number;
  distance_label: string;
  is_demo_data: boolean;
}

export interface NearbyResponse {
  items: NearbyPlace[];
  count: number;
  center: { latitude: number; longitude: number };
  radius_km: number;
  category: PlaceCategory | null;
  notice: string;
}

export interface PlaceReport {
  id: number;
  nearby_place_id: number;
  place_name: string;
  place_category: PlaceCategory;
  place_area: string | null;
  place_city: string;
  reason: string;
  description: string | null;
  status: "OPEN" | "RESOLVED" | "REJECTED";
  reporter_name: string | null;
  reviewer_notes: string | null;
  place_is_active: boolean | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ReferenceData {
  states: string[];
  /** state -> cities (major first) -> areas */
  locations: Record<string, CityRef[]>;
  place_categories: PlaceCategory[];
  place_report_reasons: string[];
  nearby_notice: string;
  property_types: string[];
  service_types: string[];
  document_types: string[];
  report_reasons: string[];
  checks: { check_type: string; label: string }[];
  disclaimer: string;
  payment_warning: string;
}
