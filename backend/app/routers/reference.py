from fastapi import APIRouter

from app.models.enums import (
    CHECK_LABELS,
    DocumentType,
    PlaceCategory,
    PlaceReportReason,
    PropertyType,
    ReportReason,
    ServiceType,
)
from app.reference import active_states, locations_payload
from app.schemas.common import DISCLAIMER, PAYMENT_WARNING
from app.services.nearby import NOTICE as NEARBY_NOTICE

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("")
def reference_data() -> dict:
    """Static lookups for forms and filters. Only states PropCheck currently serves are listed."""
    return {
        "states": active_states(),
        # state -> cities (major first) -> areas, each with LGA and approximate coordinates
        "locations": locations_payload(),
        "property_types": [p.value for p in PropertyType],
        "service_types": [s.value for s in ServiceType],
        "document_types": [d.value for d in DocumentType],
        "report_reasons": [r.value for r in ReportReason],
        "place_categories": [c.value for c in PlaceCategory],
        "place_report_reasons": [r.value for r in PlaceReportReason],
        "checks": [{"check_type": k.value, "label": v} for k, v in CHECK_LABELS.items()],
        "disclaimer": DISCLAIMER,
        "payment_warning": PAYMENT_WARNING,
        "nearby_notice": NEARBY_NOTICE,
    }
