"""Nigerian location reference data and phone helpers.

Kept as data (not tables) so coverage can grow without a migration. Location levels are
State -> City -> Area/neighbourhood, and each area carries its Local Government Area (LGA).

Only states listed in `settings.active_states` are offered anywhere in the product (filters,
selectors, validation, seed data). To launch a new state: add it to LOCATIONS below (with
coordinates), then add it to ACTIVE_STATES in the environment.
"""

import re
from dataclasses import dataclass

from app.config import settings

NIGERIAN_STATES: list[str] = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo",
    "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
    "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara",
]  # fmt: skip


@dataclass(frozen=True)
class Area:
    name: str
    lga: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float
    areas: tuple[Area, ...]
    major: bool = False  # shown first in selectors (e.g. Port Harcourt for Rivers)


# Approximate neighbourhood centres. Good enough for "what is nearby" and for centring maps.
LOCATIONS: dict[str, tuple[City, ...]] = {
    "Lagos": (
        City("Lagos", 6.5244, 3.3792, major=True, areas=(
            Area("Lekki", "Eti-Osa", 6.4474, 3.4727),
            Area("Ajah", "Eti-Osa", 6.4698, 3.5852),
            Area("Sangotedo", "Eti-Osa", 6.4720, 3.6340),
            Area("Victoria Island", "Eti-Osa", 6.4281, 3.4219),
            Area("Ikoyi", "Eti-Osa", 6.4520, 3.4350),
            Area("Yaba", "Lagos Mainland", 6.5165, 3.3893),
            Area("Surulere", "Surulere", 6.4932, 3.3561),
            Area("Ikeja", "Ikeja", 6.6018, 3.3515),
            Area("Ikeja GRA", "Ikeja", 6.5800, 3.3550),
            Area("Ojodu", "Ikeja", 6.6400, 3.3700),
            Area("Maryland", "Kosofe", 6.5700, 3.3670),
            Area("Gbagada", "Kosofe", 6.5550, 3.3890),
            Area("Magodo", "Kosofe", 6.6190, 3.3870),
            Area("Festac", "Amuwo-Odofin", 6.4660, 3.2830),
        )),
        City("Ikorodu", 6.6194, 3.5105, areas=(
            Area("Ikorodu Town", "Ikorodu", 6.6194, 3.5105),
            Area("Ebute", "Ikorodu", 6.6050, 3.4900),
        )),
    ),
    "Rivers": (
        City("Port Harcourt", 4.8156, 7.0498, major=True, areas=(
            Area("Old GRA", "Port Harcourt", 4.7760, 7.0080),
            Area("GRA Phase 2", "Port Harcourt", 4.8160, 7.0010),
            Area("D-Line", "Port Harcourt", 4.7980, 7.0050),
            Area("Trans-Amadi", "Port Harcourt", 4.8100, 7.0400),
            Area("Rumuola", "Obio-Akpor", 4.8330, 6.9970),
            Area("Rumuokoro", "Obio-Akpor", 4.8650, 7.0000),
            Area("Eliozu", "Obio-Akpor", 4.8710, 7.0350),
            Area("Woji", "Obio-Akpor", 4.8250, 7.0620),
        )),
        City("Bonny", 4.4517, 7.1675, areas=(Area("Bonny Town", "Bonny", 4.4517, 7.1675),)),
    ),
    "Enugu": (
        City("Enugu", 6.4413, 7.4988, major=True, areas=(
            Area("Independence Layout", "Enugu East", 6.4600, 7.5210),
            Area("GRA", "Enugu North", 6.4500, 7.4990),
            Area("New Haven", "Enugu East", 6.4430, 7.5100),
            Area("Trans-Ekulu", "Enugu East", 6.4790, 7.5110),
            Area("Achara Layout", "Enugu South", 6.4230, 7.4970),
            Area("Uwani", "Enugu South", 6.4310, 7.4890),
        )),
        City("Nsukka", 6.8567, 7.3958, areas=(Area("University Area", "Nsukka", 6.8670, 7.4090),)),
    ),
    "Anambra": (
        City("Awka", 6.2104, 7.0670, major=True, areas=(
            Area("Ifite", "Awka South", 6.2400, 7.1100),
            Area("Amawbia", "Awka South", 6.1930, 7.0400),
            Area("Okpuno", "Awka South", 6.2280, 7.0550),
        )),
        City("Onitsha", 6.1498, 6.7857, major=True, areas=(
            Area("GRA Onitsha", "Onitsha North", 6.1550, 6.7900),
            Area("Fegge", "Onitsha South", 6.1370, 6.7760),
            Area("Woliwo", "Onitsha North", 6.1650, 6.7980),
        )),
        City("Nnewi", 6.0177, 6.9174, areas=(Area("Nnewi Central", "Nnewi North", 6.0177, 6.9174),)),
    ),
    "Imo": (
        City("Owerri", 5.4836, 7.0333, major=True, areas=(
            Area("New Owerri", "Owerri Municipal", 5.4790, 7.0250),
            Area("Ikenegbu", "Owerri Municipal", 5.4950, 7.0380),
            Area("World Bank", "Owerri North", 5.4650, 7.0130),
            Area("Aladinma", "Owerri Municipal", 5.4980, 7.0480),
        )),
        City("Orlu", 5.7960, 7.0350, areas=(Area("Orlu Town", "Orlu", 5.7960, 7.0350),)),
    ),
}  # fmt: skip


def active_states() -> list[str]:
    """States the product currently serves, in configured order."""
    return [s.strip() for s in settings.active_states.split(",") if s.strip() in LOCATIONS]


def is_active_state(state: str) -> bool:
    return state in active_states()


def find_city(state: str, city: str) -> City | None:
    return next((c for c in LOCATIONS.get(state, ()) if c.name.lower() == city.lower()), None)


def find_area(state: str, name: str) -> tuple[City, Area] | None:
    for c in LOCATIONS.get(state, ()):
        for a in c.areas:
            if a.name.lower() == name.lower():
                return c, a
    return None


def locations_payload() -> dict[str, list[dict]]:
    """JSON shape for the frontend: state -> cities (major first) -> areas."""
    out: dict[str, list[dict]] = {}
    for state in active_states():
        cities = sorted(LOCATIONS[state], key=lambda c: (not c.major, c.name))
        out[state] = [
            {
                "city": c.name,
                "major": c.major,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "areas": [
                    {"area": a.name, "lga": a.lga, "latitude": a.latitude, "longitude": a.longitude}
                    for a in c.areas
                ],
            }
            for c in cities
        ]
    return out


_PHONE_RE = re.compile(r"^(?:\+?234|0)?([789][01]\d{8})$")


def normalize_ng_phone(raw: str) -> str:
    """Normalise a Nigerian mobile number to E.164 (+234XXXXXXXXXX). Raises ValueError if invalid."""
    digits = re.sub(r"[\s\-()]", "", raw or "")
    m = _PHONE_RE.match(digits)
    if not m:
        raise ValueError("Enter a valid Nigerian mobile number, e.g. 0803 123 4567 or +234 803 123 4567.")
    return "+234" + m.group(1)
