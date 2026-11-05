"""Requests users make for administrator help (password resets while there is
no email), and how administrators work through them."""

import logging
import math
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.account_request_db_interface import (
    close_requests_db, count_open_requests_db, get_request_by_id_db, get_visible_request_db,
    list_requests_db, open_or_bump_request_db,
)
from app.database.session import SessionLocal
from app.database.user_db_interface import get_user_by_email_db, get_user_by_id_db, get_user_by_username_db
from app.models.account_request_db_model import PASSWORD_RESET
from app.services.admin_service import issue_password
from app.utils.audit import security_event, subject_hash

logger = logging.getLogger(__name__)

RESET_REQUESTED_MESSAGE = (
    "If an account matches, an administrator has been notified and will contact you with a temporary password."
)


def visible_roles(actor) -> tuple:
    """Requests are shown only for accounts the administrator may manage."""
    return ("user", "admin") if actor.role == "root" else ("user",)


def _find_account(db: Session, identifier: str):
    # An address is looked up as an email first, so a username that looks like
    # someone's address cannot capture their requests.
    if "@" in identifier:
        return get_user_by_email_db(db, identifier) or get_user_by_username_db(db, identifier)
    return get_user_by_username_db(db, identifier) or get_user_by_email_db(db, identifier)


def queue_password_reset(identifier: str, requester_ip: str | None, user_agent: str | None) -> None:
    """Runs after the 202 is sent (a background task), so neither the response
    time nor an error reveals whether the account exists."""
    identifier = identifier.strip()
    try:
        with SessionLocal() as db:
            user = _find_account(db, identifier)
            # ROOT recovers with the CLI break-glass reset, not through other admins.
            queued = bool(user and user.role != "root")
            if queued:
                open_or_bump_request_db(db, str(user.id), PASSWORD_RESET, requester_ip, user_agent)
        security_event("password_reset_requested", subject=subject_hash(identifier), queued=queued)
    except Exception:
        logger.exception("Could not queue a password reset request")


def _serialize(request, user, resolver_username) -> dict:
    return {
        "id": request.id,
        "category": request.category,
        "status": request.status,
        "request_count": request.request_count,
        "requester_ip": request.requester_ip,
        "user_agent": request.user_agent,
        "created_at": request.created_at,
        "last_requested_at": request.last_requested_at,
        "resolved_at": request.resolved_at,
        "resolved_by_username": resolver_username,
        "user": user,
    }


def list_requests(db: Session, actor, status: str, category: str = None, page: int = 1, per_page: int = 20) -> dict:
    rows, total = list_requests_db(db, visible_roles(actor), status, category, page, per_page)
    return {
        "requests": [_serialize(*row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": math.ceil(total / per_page) if total else 1,
    }


def get_request(db: Session, actor, request_id: str) -> dict:
    row = get_visible_request_db(db, request_id, visible_roles(actor))
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    return _serialize(*row)


def request_summary(db: Session, actor) -> dict:
    return {"open": count_open_requests_db(db, visible_roles(actor))}


def _open_request_for(db: Session, actor, request_id: str):
    """The open request plus its user, or 404 when it is not visible to the actor.

    Locks the user before the request, the same order as the user-pane reset,
    so the two paths cannot deadlock each other.
    """
    request = get_request_by_id_db(db, request_id)
    user = get_user_by_id_db(db, request.user_id, for_update=True) if request else None
    if not user or user.role not in visible_roles(actor):
        raise HTTPException(status_code=404, detail="Request not found")
    request = get_request_by_id_db(db, request_id, for_update=True)
    if request.status != "open":
        raise HTTPException(status_code=409, detail=f"This request is already {request.status}")
    return request, user


def issue_password_for_request(db: Session, actor, request_id: str) -> dict:
    request, user = _open_request_for(db, actor, request_id)
    if request.category != PASSWORD_RESET:
        raise HTTPException(status_code=400, detail="This request is not a password reset")
    # issue_password resolves the user's open reset requests.
    return issue_password(db, actor, user)


def dismiss_request(db: Session, actor, request_id: str) -> dict:
    request, user = _open_request_for(db, actor, request_id)
    close_requests_db(db, str(user.id), request.category, "dismissed", str(actor.id))
    db.commit()
    security_event("account_request_dismissed", actor=str(actor.id), target=str(user.id), request=str(request.id))
    return {"message": "Request dismissed"}
