from app.models.enums import Role
from tests.helpers import create_agent, create_property, make_user


def test_register_login_me_logout(client):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Ada  Obi",
            "email": "Ada@Example.com",
            "password": "secret123",
            "phone": "0803 123 4567",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["full_name"] == "Ada Obi"
    assert body["user"]["phone"] == "+2348031234567"
    assert body["user"]["role"] == "RENTER"
    assert "password_hash" not in body["user"]
    assert "propcheck_session" in r.cookies

    me = client.get("/api/auth/me")  # cookie session
    assert me.status_code == 200 and me.json()["email"] == "ada@example.com"

    assert (
        client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong999"}).status_code
        == 401
    )
    assert (
        client.post("/api/auth/login", json={"email": "ada@example.com", "password": "secret123"}).status_code
        == 200
    )

    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_email_rejected(client):
    payload = {"full_name": "Tunde", "email": "t@example.com", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_cannot_self_register_as_reviewer(client):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Sneaky", "email": "s@example.com", "password": "secret123", "role": "REVIEWER"},
    )
    assert r.status_code == 422


def test_weak_password_and_bad_phone_rejected(client):
    r = client.post(
        "/api/auth/register", json={"full_name": "A B", "email": "a@example.com", "password": "password"}
    )
    assert r.status_code == 422
    assert "letter and one number" in r.json()["detail"]
    r = client.post(
        "/api/auth/register",
        json={"full_name": "A B", "email": "b@example.com", "password": "pass1234", "phone": "12345"},
    )
    assert r.status_code == 422


def test_unauthenticated_requests_get_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/properties", json={}).status_code in (401, 422)
    assert client.get("/api/reviewer/summary").status_code == 401


def test_role_restrictions(client, session):
    _, renter = make_user(session, Role.RENTER)
    _, agent = make_user(session, Role.AGENT)
    # Renters cannot list properties or use reviewer endpoints.
    assert client.post("/api/properties", json={"title": "x"}, headers=renter).status_code in (403, 422)
    assert client.get("/api/reviewer/summary", headers=renter).status_code == 403
    assert client.get("/api/reviewer/summary", headers=agent).status_code == 403
    # Agents cannot book inspections or create house-search requests.
    assert client.post("/api/inspection-bookings", json={"slot_id": 1}, headers=agent).status_code == 403


def test_agent_cannot_edit_another_agents_property(client, session):
    _, h1, _ = create_agent(client, session)
    _, h2, _ = create_agent(client, session)
    prop = create_property(client, h1)
    r = client.patch(f"/api/properties/{prop['id']}", json={"title": "Hijacked listing"}, headers=h2)
    assert r.status_code == 403
    r = client.patch(f"/api/properties/{prop['id']}", json={"title": "Renamed 2-bed flat"}, headers=h1)
    assert r.status_code == 200 and r.json()["title"] == "Renamed 2-bed flat"


def test_reviewer_cannot_edit_listings(client, session):
    _, h1, _ = create_agent(client, session)
    prop = create_property(client, h1)
    _, reviewer = make_user(session, Role.REVIEWER)
    assert (
        client.patch(
            f"/api/properties/{prop['id']}", json={"title": "Edited by reviewer"}, headers=reviewer
        ).status_code
        == 403
    )
