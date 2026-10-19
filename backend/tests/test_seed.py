from collections import Counter

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

import app.seed as seed_module
from app.models import (
    AgentProfile,
    AgentReport,
    AuditLog,
    HouseSearchRequest,
    InspectionBooking,
    Property,
    Reservation,
    User,
    VerificationCase,
)
from app.reference import active_states


async def _factory(session: AsyncSession):
    """Seed sessions share the test's connection, so the seed is rolled back with the test."""
    connection = await session.connection()
    return lambda: AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


async def test_demo_seed_covers_every_workflow_state(session):
    """The demo data gives reviewers something to look at in every queue, using launch states only."""
    await seed_module.seed(await _factory(session))

    async def count(model, field):
        return Counter(getattr(row, field).value for row in (await session.exec(select(model))).all())

    roles = await count(User, "role")
    assert roles["RENTER"] >= 4 and roles["AGENT"] + roles["LANDLORD"] >= 5
    assert roles["REVIEWER"] == 2 and roles["ADMIN"] == 1

    assert {p.state for p in (await session.exec(select(Property))).all()} == set(active_states())
    cases = await count(VerificationCase, "status")
    assert cases["VERIFIED"] >= 3 and cases["SUBMITTED"] + cases["IN_REVIEW"] >= 2 and cases["REJECTED"] >= 1
    rejected = (
        await session.exec(select(VerificationCase).where(VerificationCase.status == "REJECTED"))
    ).one()
    assert rejected.rejection_reason

    agents = await count(AgentProfile, "verification_status")
    assert agents["VERIFIED"] >= 4 and agents["SUSPENDED"] + agents["REJECTED"] >= 1

    assert set(await count(Reservation, "status")) >= {
        "PENDING_PAYMENT",
        "PENDING_RELEASE",
        "RELEASED",
        "REFUNDED",
    }
    assert set(await count(InspectionBooking, "status")) >= {"REQUESTED", "CONFIRMED"}
    assert set(await count(HouseSearchRequest, "status")) >= {
        "SUBMITTED",
        "ASSIGNED",
        "CONTACTED",
        "CANCELLED",
    }
    assert set(await count(AgentReport, "status")) >= {"OPEN", "RESOLVED", "REJECTED"}

    # Seeded transitions went through the state machine, so they are audited like real ones.
    actions = {a.action for a in (await session.exec(select(AuditLog))).all()}
    assert {
        "PROPERTY_VERIFIED",
        "KEYS_CONFIRMED_RELEASED",
        "RESERVATION_REFUNDED",
        "REQUEST_ASSIGNED",
    } <= actions


def test_seed_photo_files_exist():
    for photos in seed_module.REAL_PHOTOS.values():
        for filename, _caption in photos:
            assert (seed_module.SEED_ASSETS / filename).is_file(), filename


async def test_rerunning_seed_refreshes_demo_listing_photos(session):
    """An existing demo database picks up new listing photos without being reset."""
    await seed_module.seed(await _factory(session))
    assert await seed_module.sync_listing_photos(session) == 0  # already up to date

    from app.models import PropertyMedia

    lekki = (
        await session.exec(
            select(Property).where(Property.public_slug == seed_module._slug(seed_module.PROPERTIES[0][1], 0))
        )
    ).one()
    for m in (await session.exec(select(PropertyMedia).where(PropertyMedia.property_id == lekki.id))).all():
        m.caption = "Old placeholder"
        session.add(m)
    await session.flush()

    assert await seed_module.sync_listing_photos(session) == 1
    captions = [
        m.caption
        for m in (
            await session.exec(
                select(PropertyMedia).where(PropertyMedia.property_id == lekki.id).order_by(PropertyMedia.id)
            )
        ).all()
    ]
    assert captions == [c for _, c in seed_module.REAL_PHOTOS[0]]


async def test_rerunning_seed_restores_photo_files_lost_from_disk(session):
    """Free hosting wipes the disk on restart; the startup seed must put the demo photos back."""
    from app.models import PropertyMedia
    from app.services import storage

    await seed_module.seed(await _factory(session))
    lekki = (
        await session.exec(
            select(Property).where(Property.public_slug == seed_module._slug(seed_module.PROPERTIES[0][1], 0))
        )
    ).one()
    media = (await session.exec(select(PropertyMedia).where(PropertyMedia.property_id == lekki.id))).all()
    lost = storage.public_dir() / media[0].url.rsplit("/media/", 1)[1]
    lost.unlink()

    assert await seed_module.sync_listing_photos(session) == 1
    restored = (await session.exec(select(PropertyMedia).where(PropertyMedia.property_id == lekki.id))).all()
    assert all((storage.public_dir() / m.url.rsplit("/media/", 1)[1]).is_file() for m in restored)
