import pytest
from sqlmodel import select

from app.models import AuditLog, NearbyPlace, PlaceReport
from app.models.enums import PlaceCategory, Role
from app.reference import LOCATIONS, active_states, locations_payload
from app.seed_nearby import build_demo_places
from app.services.nearby import bounding_box, format_distance, haversine_km
from tests.helpers import make_user

# A point in GRA Phase 2, Port Harcourt.
ORIGIN = (4.8160, 7.0010)


def _offset(km_north: float = 0.0, km_east: float = 0.0) -> tuple[float, float]:
    import math

    lat, lng = ORIGIN
    return lat + km_north / 111.32, lng + km_east / (111.32 * math.cos(math.radians(lat)))


def add_place(session, name: str, category: PlaceCategory, km_north: float = 0.0, km_east: float = 0.0, **kw):
    lat, lng = _offset(km_north, km_east)
    place = NearbyPlace(
        name=name,
        category=category,
        state="Rivers",
        city="Port Harcourt",
        area="GRA Phase 2",
        latitude=lat,
        longitude=lng,
        source=kw.pop("source", "MANUAL"),
        **kw,
    )
    session.add(place)
    session.commit()
    session.refresh(place)
    return place


def search(client, **params):
    base = {"latitude": ORIGIN[0], "longitude": ORIGIN[1]}
    return client.get("/api/nearby-places", params={**base, **params})


# ---------------------------------------------------------------- distance maths & formatting


def test_haversine_known_distance():
    # One degree of latitude is ~111.2 km everywhere.
    assert haversine_km(4.0, 7.0, 5.0, 7.0) == pytest.approx(111.2, abs=0.2)
    assert haversine_km(*ORIGIN, *ORIGIN) == 0
    # Lagos (Yaba) to Port Harcourt is roughly 435 km as the crow flies.
    assert haversine_km(6.5165, 3.3893, 4.8156, 7.0498) == pytest.approx(435, abs=15)


def test_bounding_box_contains_circle():
    min_lat, max_lat, min_lng, max_lng = bounding_box(*ORIGIN, 5)
    assert haversine_km(*ORIGIN, max_lat, ORIGIN[1]) == pytest.approx(5, rel=0.01)
    assert haversine_km(*ORIGIN, ORIGIN[0], max_lng) == pytest.approx(5, rel=0.01)
    assert min_lat < ORIGIN[0] < max_lat and min_lng < ORIGIN[1] < max_lng


@pytest.mark.parametrize(
    ("km", "label"),
    [
        (0.004, "10 m"),
        (0.25, "250 m"),
        (0.8549, "850 m"),
        (0.996, "1.0 km"),
        (1.0, "1.0 km"),
        (1.26, "1.3 km"),
        (12.04, "12.0 km"),
    ],
)
def test_distance_formatting(km, label):
    assert format_distance(km) == label


# ---------------------------------------------------------------- search endpoint


def test_sorted_by_distance_with_distance_fields(client, session):
    add_place(session, "Far Market", PlaceCategory.MARKET, km_north=2.0)
    add_place(session, "Near Kitchen", PlaceCategory.RESTAURANT, km_east=0.3)
    add_place(session, "Middle Chapel", PlaceCategory.CHURCH, km_north=-1.0)
    r = search(client, radius_km=5)
    assert r.status_code == 200
    body = r.json()
    names = [p["name"] for p in body["items"]]
    assert names == ["Near Kitchen", "Middle Chapel", "Far Market"]
    first = body["items"][0]
    assert first["distance_m"] == pytest.approx(300, abs=5)
    assert first["distance_label"] == "300 m"
    assert body["items"][2]["distance_label"] == "2.0 km"
    assert "may change" in body["notice"]
    assert body["count"] == 3 and body["radius_km"] == 5


def test_filtered_by_category(client, session):
    add_place(session, "Corner Market", PlaceCategory.MARKET, km_north=0.2)
    add_place(session, "Palm Lounge", PlaceCategory.CLUB, km_north=0.4)
    add_place(session, "Pepper Soup Place", PlaceCategory.RESTAURANT, km_east=0.5)
    r = search(client, category="CLUB")
    assert [p["name"] for p in r.json()["items"]] == ["Palm Lounge"]
    assert r.json()["category"] == "CLUB"


def test_places_outside_radius_excluded(client, session):
    add_place(session, "Inside", PlaceCategory.MARKET, km_north=0.9)
    add_place(session, "Just outside", PlaceCategory.MARKET, km_north=1.2)
    # Inside the bounding box (corner) but outside the circle: must still be excluded.
    add_place(session, "Box corner", PlaceCategory.MARKET, km_north=0.9, km_east=0.9)
    r = search(client, radius_km=1)
    assert [p["name"] for p in r.json()["items"]] == ["Inside"]


def test_inactive_places_hidden(client, session):
    add_place(session, "Closed Market", PlaceCategory.MARKET, km_north=0.1, is_active=False)
    assert search(client).json()["items"] == []


def test_empty_results(client):
    r = client.get("/api/nearby-places", params={"latitude": 6.0, "longitude": 4.0, "radius_km": 1})
    assert r.status_code == 200
    assert r.json()["items"] == [] and r.json()["count"] == 0


def test_invalid_category_and_radius_rejected(client):
    assert search(client, category="MOSQUE_OR_BAR").status_code == 422
    assert search(client, radius_km=50).status_code == 422  # above the 10 km cap
    assert search(client, radius_km=0).status_code == 422
    assert client.get("/api/nearby-places", params={"latitude": 95, "longitude": 7}).status_code == 422
    assert client.get("/api/nearby-places", params={"longitude": 7}).status_code == 422


def test_response_hides_internal_fields(client, session):
    add_place(
        session,
        "Demo Bukka",
        PlaceCategory.RESTAURANT,
        km_north=0.1,
        source="DEMO_SEED",
        phone_number="+2348000001234",
    )
    item = search(client).json()["items"][0]
    assert item["is_demo_data"] is True
    assert item["phone_number"] == "+2348000001234"
    for hidden in ("is_active", "source", "created_at", "updated_at"):
        assert hidden not in item
    assert "verified" not in " ".join(item.keys())


# ---------------------------------------------------------------- place reports


def test_place_report_created_and_audited(client, session):
    place = add_place(session, "Wrong Hours Kitchen", PlaceCategory.RESTAURANT, km_north=0.1)
    payload = {"reason": "WRONG_OPENING_HOURS", "description": "Closes at 6pm, not 10pm."}
    assert client.post(f"/api/nearby-places/{place.id}/report", json=payload).status_code == 401

    user, headers = make_user(session, Role.RENTER)
    r = client.post(f"/api/nearby-places/{place.id}/report", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "OPEN" and body["place_name"] == "Wrong Hours Kitchen"
    assert body["reviewer_notes"] is None and body["reporter_name"] is None  # staff-only fields
    report = session.get(PlaceReport, body["id"])
    assert report.reporter_id == user.id
    assert session.exec(select(AuditLog).where(AuditLog.action == "PLACE_REPORTED")).first()
    # Same user, same place, still open -> duplicate refused.
    assert (
        client.post(f"/api/nearby-places/{place.id}/report", json=payload, headers=headers).status_code == 409
    )
    # Invalid reason and unknown place.
    assert (
        client.post(
            f"/api/nearby-places/{place.id}/report", json={"reason": "BORING"}, headers=headers
        ).status_code
        == 422
    )
    assert client.post("/api/nearby-places/999999/report", json=payload, headers=headers).status_code == 404


def test_reviewer_resolves_report_and_hides_place(client, session):
    place = add_place(session, "Gone Market", PlaceCategory.MARKET, km_north=0.1)
    _, renter = make_user(session, Role.RENTER)
    _, reviewer = make_user(session, Role.REVIEWER)
    report = client.post(
        f"/api/nearby-places/{place.id}/report", json={"reason": "PERMANENTLY_CLOSED"}, headers=renter
    ).json()

    assert client.get("/api/reviewer/place-reports", headers=renter).status_code == 403
    queue = client.get("/api/reviewer/place-reports", headers=reviewer).json()
    assert report["id"] in [q["id"] for q in queue]

    url = f"/api/reviewer/place-reports/{report['id']}/resolve"
    assert client.post(url, json={"reason": ""}, headers=reviewer).status_code == 422
    r = client.post(url, json={"reason": "Confirmed closed", "deactivate_place": True}, headers=reviewer)
    assert r.status_code == 200 and r.json()["status"] == "RESOLVED" and r.json()["place_is_active"] is False
    assert search(client).json()["items"] == []
    assert client.post(url, json={"reason": "again"}, headers=reviewer).status_code == 409


# ---------------------------------------------------------------- coverage


def test_only_five_launch_states_in_filters(client):
    ref = client.get("/api/reference").json()
    assert ref["states"] == ["Lagos", "Rivers", "Enugu", "Anambra", "Imo"]
    assert set(ref["locations"]) == {"Lagos", "Rivers", "Enugu", "Anambra", "Imo"}
    for northern in ("FCT", "Kano", "Kaduna", "Borno", "Sokoto", "Plateau"):
        assert northern not in ref["states"]
    assert ref["place_categories"] == ["MARKET", "RESTAURANT", "CHURCH", "CLUB"]


def test_port_harcourt_is_major_city_under_rivers(client):
    rivers = client.get("/api/reference").json()["locations"]["Rivers"]
    assert rivers[0]["city"] == "Port Harcourt" and rivers[0]["major"] is True
    areas = [a["area"] for a in rivers[0]["areas"]]
    assert {"GRA Phase 2", "Old GRA", "Rumuola", "Trans-Amadi"} <= set(areas)
    assert all(a["lga"] for a in rivers[0]["areas"])


def test_listings_outside_launch_states_rejected(client, session):
    from tests.helpers import PROPERTY, create_agent

    _, headers, _ = create_agent(client, session)
    r = client.post("/api/properties", json={**PROPERTY, "state": "FCT", "city": "Abuja"}, headers=headers)
    assert r.status_code == 422
    assert "does not cover FCT" in r.json()["detail"]


def test_demo_seed_covers_only_launch_states():
    places = build_demo_places()
    assert {p.state for p in places} == set(active_states())
    assert {p.category for p in places} == set(PlaceCategory)
    assert all(p.source == "DEMO_SEED" and "Demo data" in (p.description or "") for p in places)
    assert len({p.name for p in places}) == len(places)
    # Every place sits inside its state's known coordinates (within 30 km of some area centre).
    for p in places:
        centres = [(a.latitude, a.longitude) for c in LOCATIONS[p.state] for a in c.areas]
        assert min(haversine_km(p.latitude, p.longitude, *c) for c in centres) < 30


def test_locations_payload_lists_major_cities_first():
    payload = locations_payload()
    assert payload["Anambra"][0]["major"] is True
    assert [c["city"] for c in payload["Rivers"]] == ["Port Harcourt", "Bonny"]
