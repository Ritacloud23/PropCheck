from datetime import timedelta

from sqlmodel import select

from app.models import AuditLog, Property
from app.models.base import utcnow
from app.models.enums import Role
from app.services.fees import reservation_deposit, total_move_in_cost
from tests.helpers import PDF, PNG, create_agent, create_property, make_user, verified_property


async def test_agent_creates_property_as_unverified_draft(client, session):
    _, headers, profile = await create_agent(client, session)
    prop = await create_property(client, headers)
    assert prop["public_slug"] and prop["state"] == "Lagos"
    assert prop["verification"]["status"] == "NOT_SUBMITTED"
    row = await session.get(Property, prop["id"])
    assert row.listing_agent_id == profile["id"]
    audit = (
        await session.exec(
            select(AuditLog).where(AuditLog.entity_type == "Property", AuditLog.entity_id == prop["id"])
        )
    ).all()
    assert [a.action for a in audit] == ["PROPERTY_CREATED"]


async def test_total_move_in_cost_computed_server_side(client, session):
    _, headers, _ = await create_agent(client, session)
    prop = await create_property(client, headers, total_move_in_cost=1)  # client value ignored
    assert prop["fees"]["total_move_in_cost"] == 3_500_000 + 350_000 + 350_000 + 200_000 + 50_000
    r = await client.patch(f"/api/properties/{prop['id']}", json={"agency_fee": 0}, headers=headers)
    assert r.json()["fees"]["total_move_in_cost"] == 4_100_000


def test_fee_helpers():
    assert total_move_in_cost(1_000_000, 100_000, 50_000, 0, 0) == 1_150_000
    assert reservation_deposit(3_500_000) == 350_000
    assert reservation_deposit(5_000) == 1_000


async def test_negative_fee_and_unknown_state_rejected(client, session):
    _, headers, _ = await create_agent(client, session)
    r = await client.post("/api/properties", json={**_base(), "agency_fee": -1}, headers=headers)
    assert r.status_code == 422
    r = await client.post("/api/properties", json={**_base(), "state": "Atlantis"}, headers=headers)
    assert r.status_code == 422


def _base():
    from tests.helpers import PROPERTY

    return dict(PROPERTY)


async def test_search_filters(client, session):
    _, headers, _ = await create_agent(client, session)
    await create_property(client, headers, title="Mini flat in Yaba area", city="Yaba", rent_amount=900_000)
    await create_property(
        client,
        headers,
        title="Flat in GRA Phase 2 district",
        state="Rivers",
        city="Port Harcourt",
        area="GRA Phase 2",
        latitude=4.816,
        longitude=7.001,
        rent_amount=12_000_000,
    )
    r = await client.get("/api/properties", params={"state": "Rivers", "city": "Port Harcourt"})
    titles = [p["title"] for p in r.json()["items"]]
    assert "Flat in GRA Phase 2 district" in titles and "Mini flat in Yaba area" not in titles
    r = await client.get("/api/properties", params={"rent_max": 1_000_000, "state": "Lagos"})
    assert all(p["rent_amount"] <= 1_000_000 for p in r.json()["items"])
    r = await client.get("/api/properties", params={"verified_only": True, "city": "Yaba"})
    assert r.json()["total"] == 0


async def test_documents_private_photos_public(client, session):
    _, owner, _ = await create_agent(client, session)
    prop = await create_property(client, owner)
    await client.post(
        f"/api/properties/{prop['id']}/media", files={"file": ("a.png", PNG, "image/png")}, headers=owner
    )
    r = await client.post(
        f"/api/properties/{prop['id']}/documents",
        files={"file": ("auth.pdf", PDF, "application/pdf")},
        data={"document_type": "AUTHORITY_LETTER"},
        headers=owner,
    )
    assert r.json()["review_status"] == "UPLOADED"  # never trusted just because it was uploaded

    public = (await client.get(f"/api/properties/{prop['public_slug']}")).json()
    assert public["documents"] is None and public["can_manage"] is False
    assert len(public["media"]) == 1

    _, stranger = await make_user(session, Role.RENTER)
    assert (await client.get(f"/api/properties/{prop['id']}", headers=stranger)).json()["documents"] is None

    mine = (await client.get(f"/api/properties/{prop['id']}", headers=owner)).json()
    link = mine["documents"][0]["link"]
    assert link.startswith("/api/files/")
    f = await client.get(link)
    assert f.status_code == 200 and f.content == PDF
    assert (await client.get("/api/files/forged.token")).status_code == 404


async def test_upload_rejects_disguised_file(client, session):
    _, owner, _ = await create_agent(client, session)
    prop = await create_property(client, owner)
    r = await client.post(
        f"/api/properties/{prop['id']}/media",
        files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")},
        headers=owner,
    )
    assert r.status_code == 400


async def test_expired_verification_displays_as_expired(client, session):
    world = await verified_property(client, session)
    pid = world["property"]["id"]
    assert (await client.get(f"/api/properties/{pid}")).json()["verification"]["status"] == "VERIFIED"

    prop = await session.get(Property, pid)
    prop.verification_expires_at = utcnow() - timedelta(days=1)
    session.add(prop)
    await session.commit()

    detail = (await client.get(f"/api/properties/{pid}")).json()
    assert detail["verification"]["status"] == "EXPIRED"
    assert detail["verification"]["is_currently_verified"] is False
    report = (await client.get(f"/api/properties/{pid}/verification-report")).json()
    assert report["status"] == "EXPIRED" and report["is_currently_verified"] is False
    assert (await client.get("/api/properties", params={"verified_only": True})).json()["total"] == 0


async def test_material_edit_after_verification_expires_it(client, session):
    world = await verified_property(client, session)
    pid = world["property"]["id"]
    r = await client.patch(
        f"/api/properties/{pid}", json={"rent_amount": 4_000_000}, headers=world["agent_headers"]
    )
    assert r.status_code == 200
    assert r.json()["verification"]["status"] == "EXPIRED"
    log = (await session.exec(select(AuditLog).where(AuditLog.action == "VERIFICATION_EXPIRED"))).all()
    assert log and log[-1].actor_user_id is None  # system action


async def test_verification_report_contents(client, session):
    world = await verified_property(client, session)
    report = (
        await client.get(f"/api/properties/{world['property']['public_slug']}/verification-report")
    ).json()
    assert report["verification_reference"].startswith("PCV-")
    assert len(report["what_was_checked"]) == 8
    assert any("title" in item.lower() for item in report["what_was_not_checked"])
    assert "not a substitute for a formal title search" in report["disclaimer"]
    assert report["agent_verified"] is True
    assert report["expires_at"] and report["verified_at"]
    assert [t["to_status"] for t in report["timeline"]][-1] == "VERIFIED"


async def test_share_link(client, session):
    _, owner, _ = await create_agent(client, session)
    prop = await create_property(client, owner)
    r = (await client.get(f"/api/properties/{prop['id']}/share")).json()
    assert r["url"].endswith(prop["public_slug"])
    assert r["whatsapp_share_url"].startswith("https://wa.me/?text=")
    assert " " not in r["whatsapp_share_url"]


# The create/edit form sends JSON null for any text box left empty.
REPORTED_FEES = {
    "rent_amount": 900_000,
    "agency_fee": 10_000,
    "legal_fee": 50_000,
    "caution_fee": 20_000,
    "other_fees": 10_000,
    "other_fees_description": "security",
}


async def test_create_with_empty_description_and_reported_fees(client, session):
    _, headers, _ = await create_agent(client, session)
    from tests.helpers import PROPERTY

    r = await client.post(
        "/api/properties", json={**PROPERTY, **REPORTED_FEES, "description": None}, headers=headers
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["description"] == ""
    assert body["fees"] == {**REPORTED_FEES, "total_move_in_cost": 990_000}


async def test_clearing_description_on_edit(client, session):
    _, headers, _ = await create_agent(client, session)
    prop = await create_property(client, headers)
    r = await client.patch(f"/api/properties/{prop['id']}", json={"description": None}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["description"] == ""


async def test_fee_type_errors_still_name_the_field(client, session):
    _, headers, _ = await create_agent(client, session)
    from tests.helpers import PROPERTY

    r = await client.post("/api/properties", json={**PROPERTY, "agency_fee": "ten thousand"}, headers=headers)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "agency_fee"
