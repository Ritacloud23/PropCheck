from typing import Any

from sqlmodel import Session

from app.models import AuditLog

_SENSITIVE = ("password", "secret", "token", "authorization", "card", "cvv")


def _scrub(meta: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for k, v in meta.items():
        if any(s in k.lower() for s in _SENSITIVE):
            clean[k] = "[redacted]"
        elif isinstance(v, dict):
            clean[k] = _scrub(v)
        elif isinstance(v, str | int | float | bool) or v is None:
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean


def record(
    session: Session,
    *,
    actor_id: int | None,
    entity_type: str,
    entity_id: int,
    action: str,
    from_status: str | None = None,
    to_status: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit row to the current transaction. The caller commits (or everything rolls back)."""
    entry = AuditLog(
        actor_user_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        metadata_json=_scrub(metadata or {}),
    )
    session.add(entry)
    return entry
