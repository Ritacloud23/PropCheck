"""Demo data for local development: `python -m app.seed` (idempotent; skips if already seeded).

Every demo account uses the password printed at the end. Approvals go through the real state
machine so the audit log and verification reports look exactly like production data.
"""

import random
import struct
import zlib
from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import (
    AgentEnquiry,
    AgentProfile,
    AgentReport,
    AgentVerification,
    HouseSearchRequest,
    InspectionBooking,
    InspectionSlot,
    Property,
    PropertyDocument,
    PropertyMedia,
    Reservation,
    User,
    VerificationCase,
    VerificationCheck,
)
from app.models.base import utcnow
from app.models.enums import (
    AgentVerificationStatus,
    CheckResult,
    CheckType,
    DocumentReviewStatus,
    DocumentType,
    EnquiryStatus,
    FurnishedPreference,
    PropertyType,
    ReportReason,
    Role,
    SlotStatus,
    VerificationStatus,
)
from app.reference import find_area
from app.security import hash_password
from app.seed_nearby import seed_nearby_places
from app.services import audit, storage
from app.services.fees import reservation_deposit, total_move_in_cost
from app.services.state_machine import transition
from app.services.workflows import (
    AGENT_REPORT,
    AGENT_VERIFICATION,
    HOUSE_SEARCH,
    INSPECTION_BOOKING,
    RESERVATION,
    VERIFICATION_CASE,
)

DEMO_PASSWORD = "PropCheck2026"
PDF = b"%PDF-1.4\n% PropCheck demo document - not a real document\n%%EOF\n"


# ---------------------------------------------------------------- tiny PNG generator (no Pillow needed)


def _png(width: int, height: int, sky: tuple, wall: tuple, roof: tuple) -> bytes:
    rows = []
    hx0, hx1 = int(width * 0.28), int(width * 0.72)
    wall_top, ground = int(height * 0.48), int(height * 0.82)
    apex_y, mid = int(height * 0.22), width // 2
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            if y >= ground:
                c = (88, 140, 76)
            elif hx0 <= x < hx1 and wall_top <= y < ground:
                door = mid - 22 <= x < mid + 22 and y > ground - 70
                window = (
                    hx0 + 30 <= x < hx0 + 80 or hx1 - 80 <= x < hx1 - 30
                ) and wall_top + 30 <= y < wall_top + 75
                c = (70, 52, 40) if door else (170, 205, 230) if window else wall
            elif apex_y <= y < wall_top and abs(x - mid) <= (y - apex_y) * (hx1 - hx0 + 40) / 2 / (
                wall_top - apex_y
            ):
                c = roof
            else:
                t = y / height
                c = tuple(int(s * (1 - t * 0.35)) for s in sky)
            row += bytes(c)
        rows.append(bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
        + chunk(b"IEND", b"")
    )


PALETTES = [
    ((150, 196, 235), (236, 230, 214), (150, 60, 45)),
    ((160, 205, 240), (245, 245, 240), (60, 70, 90)),
    ((190, 215, 235), (222, 200, 170), (110, 50, 40)),
    ((140, 185, 225), (250, 238, 205), (30, 90, 70)),
]


_png_cache: dict[int, bytes] = {}


def photo_url(i: int) -> str:
    key = i % len(PALETTES)
    if key not in _png_cache:
        _png_cache[key] = _png(640, 420, *PALETTES[key])
    return storage.save_public_bytes(_png_cache[key], "seed", ".png")


# ---------------------------------------------------------------- data

AGENTS = [
    # name, agency, states, cities/areas covered, phone, status, public contact?, years, property types
    ("Adaeze Okafor", "Lekki Prime Realty", ["Lagos"], ["Lagos", "Lekki", "Ajah", "Victoria Island", "Ikoyi", "Sangotedo"], "08031110001", "VERIFIED", True, 9, ["FLAT", "DUPLEX", "TERRACE"]),
    ("Tunde Bakare", "Mainland Homes NG", ["Lagos"], ["Lagos", "Yaba", "Surulere", "Gbagada", "Maryland", "Ikeja"], "08031110002", "VERIFIED", True, 6, ["SELF_CONTAINED", "MINI_FLAT", "FLAT"]),
    ("Ngozi Okeke", "Coal City Homes", ["Enugu", "Anambra"], ["Enugu", "Independence Layout", "GRA", "New Haven", "Awka", "Onitsha"], "08031110003", "VERIFIED", False, 11, ["FLAT", "DUPLEX", "MINI_FLAT"]),
    ("Tamuno Briggs", "Garden City Lettings", ["Rivers"], ["Port Harcourt", "GRA Phase 2", "Old GRA", "Rumuola", "Rumuokoro", "Woji"], "08031110004", "VERIFIED", True, 7, ["FLAT", "SELF_CONTAINED", "BUNGALOW"]),
    ("Kemi Adeyemi", None, ["Lagos"], ["Lagos", "Ikeja", "Ikeja GRA", "Ojodu", "Magodo"], "08031110005", "VERIFIED", True, 5, ["FLAT", "BUNGALOW", "OFFICE"]),
    ("Segun Alabi", "Quick Rent Partners", ["Lagos"], ["Ikorodu", "Festac"], "08031110006", "SUSPENDED", True, 2, ["ROOM", "SELF_CONTAINED"]),
    ("Uche Obi", "Heartland Realtors", ["Imo"], ["Owerri", "New Owerri", "Ikenegbu", "World Bank"], "08031110007", "SUBMITTED", True, 3, ["MINI_FLAT", "FLAT"]),
]  # fmt: skip

PROPERTIES = [
    # agent idx, title, state, city, area, type, beds, rent, verify?, street / landmark
    (0, "Serviced 3-bedroom flat with BQ", "Lagos", "Lagos", "Lekki", "FLAT", 3, 6_500_000, True, "Off Admiralty Way, Lekki Phase 1"),
    (0, "4-bedroom semi-detached duplex", "Lagos", "Lagos", "Ajah", "DUPLEX", 4, 5_000_000, True, "Abraham Adesanya Estate"),
    (0, "Studio apartment near the beach", "Lagos", "Lagos", "Victoria Island", "SELF_CONTAINED", 1, 3_200_000, False, "Water Corporation Drive"),
    (1, "Newly built mini flat in Yaba", "Lagos", "Lagos", "Yaba", "MINI_FLAT", 1, 1_200_000, True, "Close to the Akoka campus gate"),
    (1, "2-bedroom flat in Gbagada Phase 2", "Lagos", "Lagos", "Gbagada", "FLAT", 2, 2_200_000, True, "Behind the general hospital"),
    (1, "Self-contained room in Surulere", "Lagos", "Lagos", "Surulere", "SELF_CONTAINED", 1, 650_000, False, "Off Adeniran Ogunsanya Street"),
    (2, "3-bedroom apartment, Independence Layout", "Enugu", "Enugu", "Independence Layout", "FLAT", 3, 3_500_000, True, "Off Nza Street, Independence Layout"),
    (2, "5-bedroom detached duplex in GRA", "Enugu", "Enugu", "GRA", "DUPLEX", 5, 9_000_000, True, "Off Ogui Road, GRA"),
    (2, "3-bedroom flat in Ifite, Awka", "Anambra", "Awka", "Ifite", "FLAT", 3, 1_800_000, True, "Near the university back gate, Ifite"),
    (2, "Mini flat in GRA Onitsha", "Anambra", "Onitsha", "GRA Onitsha", "MINI_FLAT", 1, 900_000, False, "Off Awka Road, GRA"),
    (4, "3-bedroom bungalow in Magodo GRA", "Lagos", "Lagos", "Magodo", "BUNGALOW", 3, 4_000_000, True, "Phase 2, Shangisha"),
    (4, "Open-plan office space, Ikeja GRA", "Lagos", "Lagos", "Ikeja GRA", "OFFICE", 0, 9_000_000, False, "Isaac John Street"),
    (3, "3-bedroom flat in GRA Phase 2", "Rivers", "Port Harcourt", "GRA Phase 2", "FLAT", 3, 4_500_000, True, "Off Tombia Street, GRA Phase 2"),
    (3, "2-bedroom flat in Woji", "Rivers", "Port Harcourt", "Woji", "FLAT", 2, 2_000_000, True, "Woji Estate Road"),
    (3, "Self-contained room in Rumuokoro", "Rivers", "Port Harcourt", "Rumuokoro", "SELF_CONTAINED", 1, 450_000, False, "Off Ikwerre Road, Rumuokoro"),
    (6, "2-bedroom flat in Ikenegbu Layout", "Imo", "Owerri", "Ikenegbu", "FLAT", 2, 1_500_000, False, "Off Okigwe Road, Ikenegbu"),
]  # fmt: skip

# Real interior photos (in app/seed_assets) used as the cover of some demo listings; the rest get
# generated placeholders. The home-page hero card shows listing 7 (Enugu GRA duplex).
SEED_ASSETS = Path(__file__).parent / "seed_assets"
REAL_PHOTOS = {7: ("enugu-gra-dining.jpg", "Dining area and staircase")}

# Listings whose verification case a reviewer rejects, with the reason shown on the report.
REJECTED_LISTINGS = {
    14: "Photos showed a different building from the one inspected, and the authority letter did not name the agent."
}


def _user(session: Session, name: str, email: str, role: Role, phone: str | None = None) -> User:
    user = User(
        full_name=name, email=email, phone=phone, password_hash=hash_password(DEMO_PASSWORD), role=role
    )
    session.add(user)
    session.flush()
    return user


def _seed_bookings(session: Session, props, slots, profiles, renters: list[User]) -> None:
    """One inspection request waiting for the agent, one already confirmed."""
    for renter, prop_idx, note, confirm in (
        (renters[0], 0, "Can I come with my sister? We'd like to check the water pressure.", False),
        (renters[1], 3, "I'm a student at UNILAG; mornings work best.", True),
    ):
        prop = props[prop_idx]
        slot = slots[prop.id][0]
        booking = InspectionBooking(
            property_id=prop.id, slot_id=slot.id, renter_id=renter.id, renter_note=note
        )
        slot.status = SlotStatus.BOOKED
        session.add_all([slot, booking])
        session.flush()
        audit.record(
            session, actor_id=renter.id, entity_type="InspectionBooking", entity_id=booking.id,
            action="BOOKING_REQUESTED", to_status="REQUESTED", metadata={"slot_id": slot.id, "property_id": prop.id},
        )  # fmt: skip
        if confirm:
            agent_user = session.get(User, profiles[PROPERTIES[prop_idx][0]].user_id)
            transition(
                session, INSPECTION_BOOKING, booking.id, "CONFIRMED", agent_user,
                metadata={"landlord_note": "Confirmed. Call me when you reach the estate gate."},
            )  # fmt: skip


def _seed_reservations(session: Session, props, renters: list[User], reviewer: User) -> None:
    """TEST/DEMO reservations: released, refunded, awaiting keys and awaiting payment."""

    def reserve(renter: User, prop: Property) -> Reservation:
        res = Reservation(
            property_id=prop.id,  # type: ignore[arg-type]
            renter_id=renter.id,  # type: ignore[arg-type]
            amount=reservation_deposit(prop.rent_amount),
            terms_version=settings.reservation_terms_version,
        )
        session.add(res)
        session.flush()
        audit.record(
            session, actor_id=renter.id, entity_type="Reservation", entity_id=res.id,  # type: ignore[arg-type]
            action="RESERVATION_CREATED", to_status=res.status.value,
            metadata={"property_id": prop.id, "amount": res.amount, "terms_version": res.terms_version, "test_mode": True},
        )  # fmt: skip
        return res

    def pay(res: Reservation, renter: User) -> None:
        transition(
            session, RESERVATION, res.id, "PENDING_RELEASE", renter,  # type: ignore[arg-type]
            metadata={"payment_reference": f"PCDEMO-{res.id:05d}", "payment_provider": "simulated", "test_mode": True},
        )  # fmt: skip

    renter, renter2, renter3, renter4 = renters
    released = reserve(renter, props[12])
    pay(released, renter)
    transition(session, RESERVATION, released.id, "RELEASED", renter)  # type: ignore[arg-type]

    refunded = reserve(renter2, props[13])
    pay(refunded, renter2)
    refunded.refund_requested_at = utcnow()
    refunded.refund_request_reason = (
        "Landlord asked for an extra 'documentation fee' that was not on the listing."
    )
    session.add(refunded)
    audit.record(
        session, actor_id=renter2.id, entity_type="Reservation", entity_id=refunded.id,  # type: ignore[arg-type]
        action="REFUND_REQUESTED", reason=refunded.refund_request_reason,
    )  # fmt: skip
    transition(
        session, RESERVATION, refunded.id, "REFUNDED", reviewer,  # type: ignore[arg-type]
        reason="Unlisted fee requested after payment; test deposit returned.",
    )  # fmt: skip

    pay(reserve(renter4, props[8]), renter4)  # awaiting keys
    reserve(renter3, props[4])  # awaiting payment


def _seed_requests(session: Session, profiles, renters: list[User], reviewer: User) -> None:
    """House-search requests: new, assigned (no reply yet), contacted (agent replied) and cancelled."""
    renter, renter2, renter3, renter4 = renters

    def request(renter: User, **fields) -> HouseSearchRequest:
        req = HouseSearchRequest(
            renter_id=renter.id,  # type: ignore[arg-type]
            name=renter.full_name,
            phone=renter.phone or "",
            whatsapp_number=renter.phone,
            email=renter.email,
            consent_to_share=True,
            **fields,
        )
        session.add(req)
        session.flush()
        audit.record(
            session, actor_id=renter.id, entity_type="HouseSearchRequest", entity_id=req.id,  # type: ignore[arg-type]
            action="REQUEST_SUBMITTED", to_status=req.status.value,
        )  # fmt: skip
        return req

    def assign(req: HouseSearchRequest, agent: AgentProfile) -> AgentEnquiry:
        transition(session, HOUSE_SEARCH, req.id, "MATCHING", reviewer)  # type: ignore[arg-type]
        transition(session, HOUSE_SEARCH, req.id, "ASSIGNED", reviewer, metadata={"agent_id": agent.id})  # type: ignore[arg-type]
        enquiry = AgentEnquiry(house_search_request_id=req.id, agent_id=agent.id)  # type: ignore[arg-type]
        session.add(enquiry)
        session.flush()
        return enquiry

    request(
        renter, state="Lagos", city="Lagos", area="Yaba", local_government_area="Lagos Mainland",
        property_type=PropertyType.MINI_FLAT, bedrooms=1, budget_min=800_000, budget_max=1_500_000,
        description="Close to Yaba tech hub, need water and steady power.",
    )  # fmt: skip
    assign(
        request(
            renter3, state="Enugu", city="Enugu", area="Independence Layout", local_government_area="Enugu East",
            property_type=PropertyType.FLAT, bedrooms=2, budget_min=1_500_000, budget_max=3_000_000,
            preferred_move_in_date=(utcnow() + timedelta(days=45)).date(),
            furnished_preference=FurnishedPreference.UNFURNISHED,
            description="Relocating for a new job in January. Quiet street, space for one car.",
        ),
        profiles[2],
    )  # fmt: skip
    ph = request(
        renter4, state="Rivers", city="Port Harcourt", area="GRA Phase 2", local_government_area="Port Harcourt",
        property_type=PropertyType.FLAT, bedrooms=3, budget_min=3_000_000, budget_max=5_000_000,
        description="Family of four moving from Lagos. Need a gated compound near a good school.",
    )  # fmt: skip
    enquiry = assign(ph, profiles[3])
    agent_user = session.get(User, profiles[3].user_id)
    enquiry.message = (
        "Good afternoon. I have two verified 3-bedroom flats in GRA Phase 2 within your budget. "
        "When can you inspect?"
    )
    enquiry.status = EnquiryStatus.RESPONDED
    enquiry.responded_at = utcnow()
    session.add(enquiry)
    audit.record(
        session, actor_id=agent_user.id, entity_type="HouseSearchRequest", entity_id=ph.id,  # type: ignore[union-attr,arg-type]
        action="AGENT_RESPONDED", metadata={"enquiry_id": enquiry.id},
    )  # fmt: skip
    transition(session, HOUSE_SEARCH, ph.id, "CONTACTED", agent_user)  # type: ignore[arg-type]
    cancelled = request(
        renter2, state="Lagos", city="Lagos", area="Lekki", local_government_area="Eti-Osa",
        property_type=PropertyType.SELF_CONTAINED, bedrooms=1, budget_min=900_000, budget_max=1_600_000,
    )  # fmt: skip
    transition(
        session, HOUSE_SEARCH, cancelled.id, "CANCELLED", renter2, reason="Found a place through a friend."
    )  # type: ignore[arg-type]


def _seed_reports(
    session: Session, props, profiles, renters: list[User], reviewer: User, reviewer2: User
) -> None:
    """Reports against agents and properties: two open, one resolved, one rejected."""
    renter, renter2, renter3, renter4 = renters

    def report(
        reporter: User, agent: AgentProfile, reason: ReportReason, text: str, prop=None
    ) -> AgentReport:
        r = AgentReport(
            reporter_id=reporter.id,  # type: ignore[arg-type]
            agent_id=agent.id,
            property_id=prop.id if prop else None,
            reason=reason,
            description=text,
        )
        session.add(r)
        session.flush()
        audit.record(
            session, actor_id=reporter.id, entity_type="AgentReport", entity_id=r.id,  # type: ignore[arg-type]
            action="REPORT_FILED", to_status=r.status.value,
        )  # fmt: skip
        return r

    report(
        renter2, profiles[5], ReportReason.PAYMENT_PRESSURE,
        "Agent insisted on an 'inspection fee' transfer before showing the room.",
    )  # fmt: skip
    report(
        renter3, profiles[0], ReportReason.UNEXPECTED_FEES,
        "I was told on the phone that an 'agreement fee' is charged on top of the legal fee shown here.", props[2],
    )  # fmt: skip
    resolved = report(
        renter4, profiles[1], ReportReason.MISLEADING_PHOTOS,
        "The kitchen photo on the Surulere listing looks newer than what I saw at inspection.", props[5],
    )  # fmt: skip
    transition(session, AGENT_REPORT, resolved.id, "IN_REVIEW", reviewer)  # type: ignore[arg-type]
    transition(
        session, AGENT_REPORT, resolved.id, "RESOLVED", reviewer,  # type: ignore[arg-type]
        reason="Agent replaced the outdated kitchen photo; the listing stays unverified until inspection.",
        metadata={"reviewer_notes": "Called the renter and the agent on the same day."},
    )  # fmt: skip
    rejected = report(
        renter, profiles[3], ReportReason.FAKE_IDENTITY,
        "I could not find this agency online, so I think it may be fake.",
    )  # fmt: skip
    transition(
        session, AGENT_REPORT, rejected.id, "REJECTED", reviewer2,  # type: ignore[arg-type]
        reason="Identity and CAC registration were re-checked and match; no other evidence was provided.",
    )  # fmt: skip


def seed() -> None:
    rnd = random.Random(42)
    with Session(engine) as session:
        added = seed_nearby_places(session)
        if added:
            print(f"Seeded {added} demo nearby places.")
        if session.exec(select(User).where(User.email == "admin@propcheck.ng")).first():
            print("Accounts and listings already seeded - nothing else to do.")
            return

        _user(session, "PropCheck Admin", "admin@propcheck.ng", Role.ADMIN)
        reviewer = _user(session, "Ngozi Reviewer", "reviewer@propcheck.ng", Role.REVIEWER)
        reviewer2 = _user(session, "Ibinabo Reviewer", "reviewer2@propcheck.ng", Role.REVIEWER)
        renter = _user(session, "Chioma Eze", "renter@propcheck.ng", Role.RENTER, "+2348035550001")
        renter2 = _user(session, "Obinna Nwankwo", "renter2@propcheck.ng", Role.RENTER, "+2348035550002")
        renter3 = _user(session, "Ifeoma Chukwu", "renter3@propcheck.ng", Role.RENTER, "+2348035550004")
        renter4 = _user(session, "Babajide Ogunleye", "renter4@propcheck.ng", Role.RENTER, "+2348035550005")
        landlord = _user(
            session, "Chief Olumide Balogun", "landlord@propcheck.ng", Role.LANDLORD, "+2348035550003"
        )

        profiles: list[AgentProfile] = []
        for i, (name, agency, states, cities, phone, status, public, years, types) in enumerate(AGENTS):
            email = "agent@propcheck.ng" if i == 0 else f"agent{i + 1}@propcheck.ng"
            u = _user(session, name, email, Role.AGENT, "+234" + phone[1:])
            profile = AgentProfile(
                user_id=u.id,  # type: ignore[arg-type]
                agency_name=agency,
                bio=f"{name.split()[0]} helps renters find well-documented homes in {', '.join(cities[:3])}.",
                phone_number="+234" + phone[1:],
                whatsapp_number="+234" + phone[1:],
                email=email,
                states_covered=states,
                cities_covered=cities,
                property_types=types,
                service_types=["RENTAL", "PROPERTY_MANAGEMENT"] if years > 5 else ["RENTAL"],
                budget_min=500_000,
                budget_max=30_000_000,
                years_experience=years,
                display_phone_publicly=public,
                display_email_publicly=public,
                response_time_hours=rnd.choice([1, 2, 4, 6]),
                completed_connections=rnd.randint(3, 40) if status == "VERIFIED" else 0,
                average_rating=round(rnd.uniform(4.1, 4.9), 1) if status == "VERIFIED" else None,
                total_reviews=rnd.randint(4, 30) if status == "VERIFIED" else 0,
            )
            session.add(profile)
            session.flush()
            app = AgentVerification(
                agent_profile_id=profile.id,  # type: ignore[arg-type]
                submitted_by=u.id,  # type: ignore[arg-type]
                identity_document_url=storage.save_private_bytes(PDF, "agent-docs", ".pdf"),
                evidence_notes="Demo NIN slip and CAC certificate.",
            )
            session.add(app)
            session.flush()
            transition(session, AGENT_VERIFICATION, app.id, "SUBMITTED", u)  # type: ignore[arg-type]
            if status in ("VERIFIED", "SUSPENDED"):
                transition(session, AGENT_VERIFICATION, app.id, "IN_REVIEW", reviewer)  # type: ignore[arg-type]
                transition(
                    session,
                    AGENT_VERIFICATION,
                    app.id,
                    "VERIFIED",
                    reviewer,
                    metadata={"reviewer_notes": "Identity matched NIN; CAC record seen."},
                )  # type: ignore[arg-type]
            if status == "SUSPENDED":
                transition(
                    session,
                    AGENT_VERIFICATION,
                    app.id,
                    "SUSPENDED",
                    reviewer2,
                    reason="Multiple renters reported payment pressure before inspection.",
                )  # type: ignore[arg-type]
            profiles.append(profile)

        props: list[Property] = []
        for i, (ai, title, state, city, area, ptype, beds, rent, verify, landmark) in enumerate(PROPERTIES):
            _, area_ref = find_area(state, area)  # type: ignore[misc]
            # Scatter listings a few hundred metres around the neighbourhood centre.
            lat = round(area_ref.latitude + rnd.uniform(-0.004, 0.004), 6)
            lng = round(area_ref.longitude + rnd.uniform(-0.004, 0.004), 6)
            agent = profiles[ai]
            agent_user = session.get(User, agent.user_id)
            fees = dict(
                agency_fee=rent // 10,
                legal_fee=rent // 10,
                caution_fee=rent // 20,
                other_fees=150_000 if beds >= 3 else 0,
            )
            prop = Property(
                owner_user_id=landlord.id if i in (1, 7) else agent.user_id,  # type: ignore[arg-type]
                listing_agent_id=agent.id,
                title=title,
                description=f"{title}. Water, prepaid meter and good road access. Inspection by appointment only - never pay before inspecting.",
                address=f"{rnd.randint(2, 40)} {landmark}",
                landmark=landmark,
                state=state,
                city=city,
                area=area,
                local_government_area=area_ref.lga,
                latitude=lat,
                longitude=lng,
                property_type=PropertyType(ptype),
                bedrooms=beds,
                bathrooms=max(1, beds),
                furnished=i % 4 == 0,
                rent_amount=rent,
                **fees,
                other_fees_description="Estate service charge" if fees["other_fees"] else None,
                total_move_in_cost=total_move_in_cost(rent, **fees),
                public_slug=f"{title.lower().replace(' ', '-').replace(',', '')}-{i + 1:03d}",
            )
            session.add(prop)
            session.flush()
            if i in REAL_PHOTOS:
                filename, caption = REAL_PHOTOS[i]
                url = storage.save_public_bytes((SEED_ASSETS / filename).read_bytes(), "seed", ".jpg")
                session.add(PropertyMedia(property_id=prop.id, url=url, caption=caption))  # type: ignore[arg-type]
                session.flush()  # first photo by id is the cover
            for k in range(3):
                session.add(
                    PropertyMedia(
                        property_id=prop.id,
                        url=photo_url(i + k),
                        caption=["Front view", "Living room", "Compound"][k],
                    )
                )  # type: ignore[arg-type]
            doc = PropertyDocument(
                property_id=prop.id,  # type: ignore[arg-type]
                document_type=DocumentType.AUTHORITY_LETTER,
                url=storage.save_private_bytes(PDF, "property-docs", ".pdf"),
                original_filename="authority-letter.pdf",
                uploaded_by=agent.user_id,
            )
            session.add(doc)
            audit.record(
                session,
                actor_id=agent.user_id,
                entity_type="Property",
                entity_id=prop.id,
                action="PROPERTY_CREATED",
            )  # type: ignore[arg-type]
            props.append(prop)

            if agent.verification_status == AgentVerificationStatus.SUSPENDED:
                continue
            case = VerificationCase(
                property_id=prop.id, submitted_by=agent.user_id, verification_reference=f"TMP-{i}"
            )  # type: ignore[arg-type]
            session.add(case)
            session.flush()
            case.verification_reference = f"PCV-{utcnow().year}-{case.id:05d}"
            for ct in CheckType:
                session.add(VerificationCheck(verification_case_id=case.id, check_type=ct))  # type: ignore[arg-type]
            session.flush()
            transition(session, VERIFICATION_CASE, case.id, "SUBMITTED", agent_user)  # type: ignore[arg-type]
            if i in REJECTED_LISTINGS:
                transition(session, VERIFICATION_CASE, case.id, "IN_REVIEW", reviewer2)  # type: ignore[arg-type]
                photos = session.exec(
                    select(VerificationCheck).where(
                        VerificationCheck.verification_case_id == case.id,
                        VerificationCheck.check_type == CheckType.PHOTOS_MATCH_INSPECTION,
                    )
                ).one()
                photos.result = CheckResult.FAILED
                photos.evidence_note = "Listing photos do not match the building at the inspected address."
                photos.completed_by = reviewer2.id
                photos.completed_at = utcnow()
                doc.review_status = DocumentReviewStatus.REJECTED
                doc.reviewer_notes = "Letter is unsigned and names a different agency."
                doc.reviewed_at = utcnow()
                session.add_all([photos, doc])
                transition(
                    session, VERIFICATION_CASE, case.id, "REJECTED", reviewer2, reason=REJECTED_LISTINGS[i]
                )  # type: ignore[arg-type]
                continue
            if not verify:
                if i % 2 == 0:
                    transition(session, VERIFICATION_CASE, case.id, "IN_REVIEW", reviewer)  # type: ignore[arg-type]
                continue
            transition(session, VERIFICATION_CASE, case.id, "IN_REVIEW", reviewer)  # type: ignore[arg-type]
            transition(
                session,
                VERIFICATION_CASE,
                case.id,
                "INSPECTION_BOOKED",
                reviewer,
                metadata={"inspection_scheduled_for": (utcnow() - timedelta(days=3)).isoformat()},
            )  # type: ignore[arg-type]
            now = utcnow()
            for check in session.exec(
                select(VerificationCheck).where(VerificationCheck.verification_case_id == case.id)
            ).all():
                optional_na = (
                    check.check_type == CheckType.OWNER_CONTACT_CONFIRMED
                    and prop.owner_user_id == agent.user_id
                )
                check.result = CheckResult.NOT_APPLICABLE if optional_na else CheckResult.PASSED
                check.evidence_note = (
                    "Agent is the owner's appointed manager."
                    if optional_na
                    else "Confirmed during physical inspection."
                )
                check.completed_by = reviewer.id
                check.completed_at = now
                session.add(check)
            doc.review_status = DocumentReviewStatus.ACCEPTED
            doc.reviewed_at = now
            session.add(doc)
            session.flush()
            transition(
                session,
                VERIFICATION_CASE,
                case.id,
                "VERIFIED",
                reviewer,
                metadata={"inspected_at": (now - timedelta(days=3)).isoformat()},
            )  # type: ignore[arg-type]

        # Inspection slots for the next week on verified listings.
        slots: dict[int, list[InspectionSlot]] = {}
        for prop in props:
            if prop.verification_status.value != VerificationStatus.VERIFIED.value:
                continue
            base = (utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
            for d in range(0, 6, 2):
                start = base + timedelta(days=d)
                slot = InspectionSlot(
                    property_id=prop.id,  # type: ignore[arg-type]
                    landlord_user_id=prop.owner_user_id,
                    start_time=start,
                    end_time=start + timedelta(hours=1),
                )
                session.add(slot)
                slots.setdefault(prop.id, []).append(slot)  # type: ignore[arg-type]
        session.flush()

        _seed_bookings(session, props, slots, profiles, [renter, renter3])
        _seed_reservations(session, props, [renter, renter2, renter3, renter4], reviewer2)
        _seed_requests(session, profiles, [renter, renter2, renter3, renter4], reviewer)
        _seed_reports(session, props, profiles, [renter, renter2, renter3, renter4], reviewer, reviewer2)
        session.commit()

    print("Seeded PropCheck demo data. Password for every account:", DEMO_PASSWORD)
    for email in (
        "admin@propcheck.ng",
        "reviewer@propcheck.ng",
        "agent@propcheck.ng",
        "landlord@propcheck.ng",
        "renter@propcheck.ng",
    ):
        print("  ", email)


if __name__ == "__main__":
    seed()
