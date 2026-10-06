"""Fictional DEMO nearby places for the five launch states (Lagos, Rivers, Enugu, Anambra, Imo).

Every name here is invented, rows are marked `source="DEMO_SEED"`, and descriptions say so.
Positions are generated deterministically around each neighbourhood centre in app/reference,
so every seeded listing has markets, restaurants, churches and clubs within a few kilometres.
Phone numbers use an obviously fake 0800 000 0xxx pattern.
"""

import math
import random

from sqlmodel import Session, func, select

from app.models import NearbyPlace
from app.models.enums import PlaceCategory
from app.reference import LOCATIONS, active_states

DEMO_SOURCE = "DEMO_SEED"

NAMES: dict[PlaceCategory, list[str]] = {
    PlaceCategory.MARKET: [
        "{area} Daily Market",
        "{area} Farmers' Market",
        "{area} Community Market",
        "{area} Evening Market",
        "Mama Put Market Square, {area}",
        "{area} Fresh Produce Market",
    ],
    PlaceCategory.RESTAURANT: [
        "Mama Ifeoma's Kitchen",
        "Bukka Corner",
        "Pepper Soup Place",
        "Calabar Pot",
        "Suya Junction",
        "Nkwobi House",
        "Amala Spot",
        "Jollof & Grill",
        "Abacha Corner",
        "Ofe Owerri Kitchen",
        "Seafood Shack",
        "Rice & Stew Hub",
    ],
    PlaceCategory.CHURCH: [
        "Living Waters Chapel",
        "Grace Assembly",
        "St. Jude's Parish",
        "Hope Gospel Centre",
        "Christ the Light Parish",
        "New Covenant Church",
        "Faith Tabernacle Fellowship",
        "Mount Zion Assembly",
    ],
    PlaceCategory.CLUB: [
        "Palm Lounge",
        "Rhythm House",
        "Afrobeat Social Club",
        "Sky Deck Lounge",
        "Highlife Bar & Club",
        "The Groove Room",
        "Starlight Lounge",
        "Bluewave Club",
    ],
}

HOURS: dict[PlaceCategory, list[str | None]] = {
    PlaceCategory.MARKET: ["Mon–Sat 7:00–19:00", "Daily 6:30–20:00", None],
    PlaceCategory.RESTAURANT: ["Daily 10:00–22:00", "Mon–Sat 8:00–21:00", "Daily 11:00–23:00"],
    PlaceCategory.CHURCH: [
        "Sun services 7:00, 9:00, 11:00 · Wed 18:00",
        "Sun 8:00 & 10:30 · Fri 17:30",
        None,
    ],
    PlaceCategory.CLUB: ["Thu–Sun 20:00–03:00", "Fri–Sat 21:00–04:00", None],
}

DESCRIPTION = {
    PlaceCategory.MARKET: "Demo data · fresh produce, provisions and household items.",
    PlaceCategory.RESTAURANT: "Demo data · local dishes, eat-in and takeaway.",
    PlaceCategory.CHURCH: "Demo data · weekly services.",
    PlaceCategory.CLUB: "Demo data · music and evening lounge.",
}

STREETS = [
    "Market Road",
    "Church Street",
    "Old Road",
    "New Layout Road",
    "Ring Road",
    "Bank Road",
    "School Road",
]


def _offset(lat: float, lng: float, km: float, bearing_deg: float) -> tuple[float, float]:
    b = math.radians(bearing_deg)
    dlat = (km / 111.32) * math.cos(b)
    dlng = (km / (111.32 * math.cos(math.radians(lat)))) * math.sin(b)
    return round(lat + dlat, 6), round(lng + dlng, 6)


def build_demo_places() -> list[NearbyPlace]:
    rnd = random.Random(2026)
    places: list[NearbyPlace] = []
    used: set[str] = set()
    for state in active_states():
        for city in LOCATIONS[state]:
            for area in city.areas:
                for category in PlaceCategory:
                    # Two places per category per neighbourhood: one close, one a little further out.
                    for distance_km in (rnd.uniform(0.25, 0.9), rnd.uniform(1.0, 2.6)):
                        template = rnd.choice(NAMES[category])
                        name = template.format(area=area.name)
                        if "{area}" not in template:
                            name = f"{name}, {area.name}"
                        if name in used:
                            continue
                        used.add(name)
                        lat, lng = _offset(area.latitude, area.longitude, distance_km, rnd.uniform(0, 360))
                        has_phone = (
                            category in (PlaceCategory.RESTAURANT, PlaceCategory.CLUB) and rnd.random() < 0.7
                        )
                        places.append(
                            NearbyPlace(
                                name=name,
                                category=category,
                                description=DESCRIPTION[category],
                                address=f"{rnd.randint(1, 60)} {rnd.choice(STREETS)}, {area.name}",
                                state=state,
                                city=city.name,
                                local_government_area=area.lga,
                                area=area.name,
                                latitude=lat,
                                longitude=lng,
                                phone_number=f"+234800000{rnd.randint(1000, 9999)}" if has_phone else None,
                                opening_hours=rnd.choice(HOURS[category]),
                                source=DEMO_SOURCE,
                            )
                        )
    return places


def seed_nearby_places(session: Session) -> int:
    """Insert demo places once. Returns the number inserted (0 if places already exist)."""
    if session.exec(select(func.count()).select_from(NearbyPlace)).one():
        return 0
    places = build_demo_places()
    session.add_all(places)
    session.commit()
    return len(places)
