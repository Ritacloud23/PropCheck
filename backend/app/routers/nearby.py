from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import col, select

from app.config import settings
from app.deps import CurrentUser, SessionDep, StaffUser
from app.errors import Conflict, NotFound
from app.models import NearbyPlace, PlaceReport, User
from app.models.enums import PlaceCategory, PlaceReportStatus
from app.schemas.nearby import (
    GeoPoint,
    NearbyPlaceOut,
    NearbyResponse,
    PlaceReportDecisionIn,
    PlaceReportIn,
    PlaceReportOut,
)
from app.services import audit, nearby, presenters
from app.services.ratelimit import auth_rate_limit
from app.services.state_machine import transition
from app.services.workflows import PLACE_REPORT

router = APIRouter(tags=["nearby"])


def place_out(result: nearby.NearbyResult) -> NearbyPlaceOut:
    p = result.place
    return NearbyPlaceOut(
        id=p.id,  # type: ignore[arg-type]
        name=p.name,
        category=p.category,
        description=p.description,
        address=p.address,
        area=p.area,
        city=p.city,
        local_government_area=p.local_government_area,
        state=p.state,
        latitude=p.latitude,
        longitude=p.longitude,
        phone_number=p.phone_number,
        website_url=p.website_url,
        opening_hours=p.opening_hours,
        distance_km=round(result.distance_km, 3),
        distance_m=int(round(result.distance_km * 1000)),
        distance_label=nearby.format_distance(result.distance_km),
        is_demo_data=p.source == "DEMO_SEED",
    )


@router.get("/api/nearby-places", response_model=NearbyResponse)
def nearby_places(
    session: SessionDep,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    category: PlaceCategory | None = Query(default=None, description="MARKET, RESTAURANT, CHURCH or CLUB"),
    radius_km: float = Query(
        default=settings.nearby_default_radius_km,
        gt=0,
        le=settings.nearby_max_radius_km,
        description=f"Search radius, at most {settings.nearby_max_radius_km:g} km",
    ),
    limit: int = Query(default=30, ge=1, le=nearby.MAX_RESULTS),
) -> NearbyResponse:
    """Places within `radius_km` of a point, nearest first. Empty `items` when nothing is close."""
    results = nearby.get_provider(session).search(
        latitude=latitude, longitude=longitude, radius_km=radius_km, category=category, limit=limit
    )
    items = [place_out(r) for r in results]
    return NearbyResponse(
        items=items,
        count=len(items),
        center=GeoPoint(latitude=latitude, longitude=longitude),
        radius_km=radius_km,
        category=category,
        notice=nearby.NOTICE,
    )


def report_out(session, report: PlaceReport, viewer: User) -> PlaceReportOut:
    place = session.get(NearbyPlace, report.nearby_place_id)
    staff = presenters.STAFF
    is_staff = viewer.role in staff
    return PlaceReportOut(
        id=report.id,  # type: ignore[arg-type]
        nearby_place_id=report.nearby_place_id,
        place_name=place.name,
        place_category=place.category,
        place_area=place.area,
        place_city=place.city,
        reason=report.reason,
        description=report.description,
        status=report.status,
        reporter_name=presenters.user_names(session, [report.reporter_id]).get(report.reporter_id)
        if is_staff
        else None,
        reviewer_notes=report.reviewer_notes if is_staff else None,
        place_is_active=place.is_active if is_staff else None,
        created_at=report.created_at,
        resolved_at=report.resolved_at,
    )


@router.post(
    "/api/nearby-places/{place_id}/report",
    response_model=PlaceReportOut,
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
def report_place(
    place_id: int, body: PlaceReportIn, user: CurrentUser, session: SessionDep
) -> PlaceReportOut:
    """Report incorrect information about a nearby place. A reviewer checks every report."""
    place = session.get(NearbyPlace, place_id)
    if not place or not place.is_active:
        raise NotFound("Place not found.")
    duplicate = session.exec(
        select(PlaceReport).where(
            PlaceReport.nearby_place_id == place_id,
            PlaceReport.reporter_id == user.id,
            PlaceReport.status == PlaceReportStatus.OPEN,
        )
    ).first()
    if duplicate:
        raise Conflict("You have already reported this place. A reviewer will look at it soon.")
    report = PlaceReport(
        nearby_place_id=place_id,
        reporter_id=user.id,  # type: ignore[arg-type]
        reason=body.reason,
        description=(body.description or "").strip() or None,
    )
    session.add(report)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="PlaceReport", entity_id=report.id,  # type: ignore[arg-type]
        action="PLACE_REPORTED", to_status=report.status.value,
        metadata={"nearby_place_id": place_id, "reason": body.reason.value},
    )  # fmt: skip
    session.commit()
    session.refresh(report)
    return report_out(session, report, user)


# ---------------------------------------------------------------- reviewer queue


@router.get("/api/reviewer/place-reports", response_model=list[PlaceReportOut])
def list_place_reports(
    user: StaffUser,
    session: SessionDep,
    status: PlaceReportStatus = PlaceReportStatus.OPEN,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[PlaceReportOut]:
    rows = session.exec(
        select(PlaceReport)
        .where(PlaceReport.status == status)
        .order_by(col(PlaceReport.id).desc())
        .limit(limit)
    ).all()
    return [report_out(session, r, user) for r in rows]


@router.post("/api/reviewer/place-reports/{report_id}/{decision}", response_model=PlaceReportOut)
def decide_place_report(
    report_id: int,
    decision: Literal["resolve", "reject"],
    body: PlaceReportDecisionIn,
    user: StaffUser,
    session: SessionDep,
) -> PlaceReportOut:
    """Resolve (optionally hiding the place until it is corrected) or reject a report."""
    target = PlaceReportStatus.RESOLVED if decision == "resolve" else PlaceReportStatus.REJECTED
    meta = {"reviewer_notes": body.reviewer_notes} if body.reviewer_notes else {}
    report = transition(session, PLACE_REPORT, report_id, target, user, reason=body.reason, metadata=meta)
    if body.deactivate_place:
        if decision != "resolve":
            raise Conflict("Only a resolved report can hide a place.")
        place = session.get(NearbyPlace, report.nearby_place_id)
        if place and place.is_active:
            place.is_active = False
            session.add(place)
            audit.record(
                session, actor_id=user.id, entity_type="NearbyPlace", entity_id=place.id,  # type: ignore[arg-type]
                action="PLACE_DEACTIVATED", reason=f"Place report #{report.id}: {body.reason}",
            )  # fmt: skip
    session.commit()
    session.refresh(report)
    return report_out(session, report, user)
