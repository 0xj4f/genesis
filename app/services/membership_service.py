"""Which service a request comes from, and the account's membership there.

One account works on every service that shares this Genesis. What differs per service:
- the password policy used when the account is created (or its password changed) there;
- the membership: pending until the first sign-in there, then active; an administrator of
  that service can suspend it without touching the other services;
- the role: "admin" on one service is a regular user everywhere else. Only "root" is global.

Requests without a service (no Origin header, or Genesis' own pages) work in "Genesis
context": the global role applies and memberships are left alone.
"""

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.service_db_model import (
    ACTIVE, JOINED_AUTO, JOINED_LOGIN, JOINED_REGISTRATION, PENDING, SUSPENDED, Service, ServiceMembership,
)
from app.models.user_db_model import User
from app.utils.audit import security_event

settings = get_settings()

ACCOUNT_DEACTIVATED = "User account is deactivated"


# ---- Which service is calling? ------------------------------------------------------

def resolve_service(request: Request, client_id: str | None = None) -> str | None:
    """The calling service's client_id, or None for Genesis context.

    The browser's Origin header names the service. An explicit client_id (form or body)
    must agree with it. Any other origin is refused before credentials are checked.
    """
    origin = request.headers.get("origin")
    by_origin = settings.service_for_origin(origin) if origin else None
    if origin and not by_origin and origin.rstrip("/") not in _genesis_origins():
        security_event("authz_denied", action="unknown_origin", reason="origin_not_registered")
        raise HTTPException(status_code=403, detail="This application is not registered with Genesis")
    if client_id:
        named = settings.service_by_id(client_id)
        if not named or (origin and (not by_origin or by_origin.client_id != client_id)):
            raise HTTPException(status_code=400, detail="client_id does not match this application")
        return named.client_id
    return by_origin.client_id if by_origin else None


def _genesis_origins() -> set[str]:
    origins = {o.strip().rstrip("/") for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()}
    if settings.frontend_url:
        origins.add(settings.frontend_url)
    return origins


def password_policy_for(service_id: str | None) -> str:
    service = settings.service_by_id(service_id) if service_id else None
    return service.password_policy if service else "strict"


# ---- Memberships ---------------------------------------------------------------------

def get_membership(db: Session, user_id: str, service_id: str, for_update: bool = False):
    query = db.query(ServiceMembership).filter(
        ServiceMembership.user_id == str(user_id), ServiceMembership.service_id == service_id,
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def _auto_enroll_ids(db: Session) -> list[str]:
    rows = db.query(Service.client_id).filter(Service.is_active == True, Service.auto_enroll == True).all()  # noqa: E712
    return [row[0] for row in rows]


def enroll_new_user(db: Session, user: User, service_id: str | None) -> None:
    """A new account: active where it signed up, pending on every other auto-enroll service.

    Adds rows to the session; the caller commits.
    """
    now = datetime.utcnow()
    if service_id:
        db.add(ServiceMembership(user_id=str(user.id), service_id=service_id, status=ACTIVE,
                                 joined_via=JOINED_REGISTRATION, activated_at=now))
    for other in _auto_enroll_ids(db):
        if other != service_id:
            db.add(ServiceMembership(user_id=str(user.id), service_id=other, status=PENDING, joined_via=JOINED_AUTO))


def activate_on_login(db: Session, user: User, service_id: str | None):
    """Called on every password sign-in. Returns the membership (None for Genesis context or root).

    pending -> active (first sign-in here); suspended -> 403. An account without a row
    joins an auto-enroll service on the spot; any other service refuses it.
    """
    if not service_id or user.role == "root":
        return None
    service = db.get(Service, service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=403, detail="This application is not available")
    now = datetime.utcnow()
    membership = get_membership(db, user.id, service_id, for_update=True)
    if membership is None:
        if not service.auto_enroll:
            raise HTTPException(status_code=403, detail="This account has no access to this application")
        membership = ServiceMembership(user_id=str(user.id), service_id=service_id, status=PENDING, joined_via=JOINED_LOGIN)
        db.add(membership)
        try:
            db.flush()
        except IntegrityError:  # a concurrent first sign-in created it
            db.rollback()
            membership = get_membership(db, user.id, service_id, for_update=True)
    if membership.status == SUSPENDED:
        security_event("login_failed", user_id=str(user.id), reason="membership_suspended", service=service_id)
        raise HTTPException(status_code=403, detail=ACCOUNT_DEACTIVATED)
    if membership.status == PENDING:
        membership.status = ACTIVE
        membership.activated_at = now
        security_event("membership_activated", user_id=str(user.id), service=service_id,
                       joined_via=membership.joined_via)
    membership.last_login_at = now
    return membership


# ---- The signed-in user's scope ------------------------------------------------------

@dataclass
class Member:
    """An account as one service sees it: what the access policy (app/auth/policy.py) reads."""
    id: str
    role: str


def apply_scope(db: Session, user: User, service_id: str | None) -> None:
    """Attach the token's service to the authenticated user for this request.

    Sets user.scope_service, user.scope_role and user.scope_membership (plain attributes,
    never stored). A membership that is not active refuses the request.
    """
    user.scope_service = service_id
    user.scope_membership = None
    user.scope_role = user.role
    if not service_id or user.role == "root":
        return
    membership = get_membership(db, user.id, service_id)
    if membership is None or membership.status != ACTIVE:
        raise HTTPException(status_code=403, detail=ACCOUNT_DEACTIVATED)
    user.scope_membership = membership
    user.scope_role = membership.role


def effective_role(user: User, membership) -> str:
    """The role a token carries: root everywhere, else the membership's role (or the global one)."""
    if user.role == "root" or membership is None:
        return user.role
    return membership.role


def scoped_role(user) -> str:
    return getattr(user, "scope_role", None) or user.role


def scope_service(user) -> str | None:
    return getattr(user, "scope_service", None)


def as_member(user) -> Member:
    return Member(id=str(user.id), role=scoped_role(user))


def target_in_scope(db: Session, actor, target: User, for_update: bool = False):
    """How the actor's service sees the target: (Member, membership or None).

    Service administrators only see accounts that are active or suspended on their
    service; anything else is "not found", so other services' users can't be probed.
    """
    service_id = scope_service(actor)
    if not service_id:
        return Member(id=str(target.id), role=target.role), None
    if target.role == "root":
        return Member(id=str(target.id), role="root"), None
    membership = get_membership(db, target.id, service_id, for_update=for_update)
    if membership is None or membership.status == PENDING:
        raise HTTPException(status_code=404, detail="User not found")
    return Member(id=str(target.id), role=membership.role), membership


# ---- Startup: copy the declared services into the database ---------------------------

def sync_services(db: Session | None = None) -> None:
    """Make the services table match SERVICES, and give every account a pending
    membership in each auto-enroll service it doesn't belong to yet. Safe to repeat."""
    from app.database.session import SessionLocal

    own_session = db is None
    db = db or SessionLocal()
    try:
        declared = {service.client_id: service for service in settings.SERVICES}
        for row in db.query(Service).all():
            if row.client_id not in declared:
                row.is_active = False
        for client_id, service in declared.items():
            row = db.get(Service, client_id) or Service(client_id=client_id)
            row.name = service.name
            row.password_policy = service.password_policy
            row.auto_enroll = service.auto_enroll
            row.is_active = True
            db.add(row)
        db.flush()
        added = 0
        for client_id in _auto_enroll_ids(db):
            members = db.query(ServiceMembership.user_id).filter(ServiceMembership.service_id == client_id)
            missing = db.query(User.id).filter(User.role != "root", ~User.id.in_(members)).all()
            for (user_id,) in missing:
                db.add(ServiceMembership(user_id=user_id, service_id=client_id, status=PENDING, joined_via=JOINED_AUTO))
            added += len(missing)
        db.commit()
        if added:
            security_event("memberships_backfilled", count=added)
    finally:
        if own_session:
            db.close()
