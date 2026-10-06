"""Reusable workflow state-transition engine.

Every status change in PropCheck goes through `transition()`. Allowed transitions are
declared as data (`StateMachine.transitions`), and one call:

1. locks the entity row (SELECT ... FOR UPDATE) so concurrent duplicate operations serialise,
2. rejects transitions not in the table (HTTP 409); this also blocks repeats such as a second release,
3. checks the actor's role (HTTP 403),
4. runs guards (ownership, conflict-of-interest, business preconditions),
5. applies the new status and side effects,
6. writes an AuditLog row in the same transaction.

The engine never commits. The calling service commits once at the end, so a failure at
any point (including after an earlier transition in the same request) rolls back everything.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlmodel import Session, SQLModel, select

from app.errors import BadRequest, Forbidden, InvalidTransition, NotFound
from app.models import User
from app.models.enums import Role
from app.services import audit


@dataclass
class TransitionContext:
    session: Session
    entity: Any
    actor: User | None  # None means the system itself (e.g. scheduled expiry)
    from_status: str
    to_status: str
    reason: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def actor_id(self) -> int | None:
        return self.actor.id if self.actor else None


Guard = Callable[[TransitionContext], None]
Hook = Callable[[TransitionContext], None]


@dataclass(frozen=True)
class Rule:
    roles: frozenset[Role]
    guards: tuple[Guard, ...] = ()
    reason_required: bool = False
    action: str | None = None  # audit action name; defaults to "TRANSITION_<TO>"


@dataclass(frozen=True)
class StateMachine:
    entity_type: str
    model: type[SQLModel]
    transitions: Mapping[tuple[str, str], Rule]
    on_apply: Hook | None = None
    status_attr: str = "status"

    def allowed_targets(self, current: str) -> list[str]:
        return [to for (frm, to) in self.transitions if frm == _value(current)]

    def can(self, current: str, to: str) -> bool:
        return (_value(current), _value(to)) in self.transitions


def _value(status: Any) -> str:
    return status.value if isinstance(status, Enum) else str(status)


def transition(
    session: Session,
    machine: StateMachine,
    entity_id: int,
    to_status: str | Enum,
    actor: User | None,
    *,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    model = machine.model
    entity = session.exec(
        select(model)
        .where(model.id == entity_id)  # type: ignore[attr-defined]
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if entity is None:
        raise NotFound(f"{machine.entity_type} not found.")

    current = _value(getattr(entity, machine.status_attr))
    target = _value(to_status)
    rule = machine.transitions.get((current, target))
    if rule is None:
        if current == target:
            raise InvalidTransition(f"This {machine.entity_type.lower()} is already {current}.")
        raise InvalidTransition(f"Cannot move {machine.entity_type.lower()} from {current} to {target}.")

    if actor is not None and actor.role not in rule.roles:
        raise Forbidden("Your role is not allowed to perform this status change.")

    reason = (reason or "").strip() or None
    if rule.reason_required and not reason:
        raise BadRequest("A reason is required for this action.")

    ctx = TransitionContext(
        session=session,
        entity=entity,
        actor=actor,
        from_status=current,
        to_status=target,
        reason=reason,
        metadata=dict(metadata or {}),
    )
    if actor is not None:
        for guard in rule.guards:
            guard(ctx)

    setattr(entity, machine.status_attr, getattr(entity, machine.status_attr).__class__(target))
    if machine.on_apply:
        machine.on_apply(ctx)
    session.add(entity)

    audit.record(
        session,
        actor_id=ctx.actor_id,
        entity_type=machine.entity_type,
        entity_id=entity_id,
        action=rule.action or f"TRANSITION_{target}",
        from_status=current,
        to_status=target,
        reason=reason,
        metadata=ctx.metadata,
    )
    session.flush()
    return entity
