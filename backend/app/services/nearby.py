"""Nearby places ("What is nearby?").

Lookups go through a `NearbyProvider`. The MVP ships `DatabaseNearbyProvider`, which reads
curated rows from PostgreSQL, so local development and demos never depend on a live external
API. A future provider (e.g. OpenStreetMap Overpass) can implement the same `search()` and be
selected in `get_provider()`, ideally writing results back into `nearby_place` as a cache.

Distance is the Haversine great-circle distance. A latitude/longitude bounding box (indexed)
narrows candidates in SQL first, then exact distances are computed in Python. That is cheap at
city scale and needs no PostGIS extension.
"""

import math
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session, col, select

from app.models import NearbyPlace
from app.models.enums import PlaceCategory

EARTH_RADIUS_KM = 6371.0088
MAX_RESULTS = 50

NOTICE = (
    "Nearby information is provided for convenience and may change. "
    "Confirm opening hours, availability and directions before travelling."
)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """(min_lat, max_lat, min_lng, max_lng) that contains the whole search circle."""
    dlat = math.degrees(radius_km / EARTH_RADIUS_KM)
    # Longitude degrees shrink with latitude; guard the poles (irrelevant for Nigeria, but safe).
    dlng = math.degrees(radius_km / (EARTH_RADIUS_KM * max(math.cos(math.radians(lat)), 1e-6)))
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng


def format_distance(km: float) -> str:
    """Under 1 km: metres (nearest 10 m). 1 km or more: kilometres to one decimal place."""
    if km < 1:
        metres = max(10, int(round(km * 1000 / 10.0)) * 10)
        return "1.0 km" if metres >= 1000 else f"{metres} m"
    return f"{km:.1f} km"


@dataclass
class NearbyResult:
    place: NearbyPlace
    distance_km: float


class NearbyProvider(Protocol):
    name: str

    def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        category: PlaceCategory | None,
        limit: int,
    ) -> list[NearbyResult]: ...


class DatabaseNearbyProvider:
    name = "database"

    def __init__(self, session: Session):
        self.session = session

    def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        category: PlaceCategory | None,
        limit: int,
    ) -> list[NearbyResult]:
        min_lat, max_lat, min_lng, max_lng = bounding_box(latitude, longitude, radius_km)
        query = select(NearbyPlace).where(
            NearbyPlace.is_active == True,  # noqa: E712
            col(NearbyPlace.latitude).between(min_lat, max_lat),
            col(NearbyPlace.longitude).between(min_lng, max_lng),
        )
        if category:
            query = query.where(NearbyPlace.category == category)
        results = []
        for place in self.session.exec(query).all():
            d = haversine_km(latitude, longitude, place.latitude, place.longitude)
            if d <= radius_km:
                results.append(NearbyResult(place, d))
        results.sort(key=lambda r: (r.distance_km, r.place.id))
        return results[:limit]


def get_provider(session: Session) -> NearbyProvider:
    # TODO: add an OverpassNearbyProvider (OpenStreetMap) behind a setting, keeping this as fallback.
    return DatabaseNearbyProvider(session)
