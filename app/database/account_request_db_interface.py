from datetime import datetime
from sqlalchemy.orm import Session, aliased

from app.models.account_request_db_model import AccountRequest
from app.models.user_db_model import User


def get_open_request_db(db: Session, user_id: str, category: str):
    return db.query(AccountRequest).filter(
        AccountRequest.user_id == user_id,
        AccountRequest.category == category,
        AccountRequest.status == "open",
    ).first()


def open_or_bump_request_db(db: Session, user_id: str, category: str, requester_ip: str, user_agent: str):
    """One open request per user and category: a repeat bumps the count.

    No locking read: a locked gap on an empty range deadlocks concurrent first
    requests. A rare race can leave two open rows, which close together anyway.
    """
    now = datetime.utcnow()
    bumped = db.query(AccountRequest).filter(
        AccountRequest.user_id == user_id,
        AccountRequest.category == category,
        AccountRequest.status == "open",
    ).update(
        {
            AccountRequest.request_count: AccountRequest.request_count + 1,
            AccountRequest.last_requested_at: now,
            AccountRequest.requester_ip: requester_ip,
            AccountRequest.user_agent: user_agent,
        },
        synchronize_session=False,
    )
    if not bumped:
        db.add(AccountRequest(
            user_id=user_id, category=category, status="open", request_count=1,
            requester_ip=requester_ip, user_agent=user_agent, created_at=now, last_requested_at=now,
        ))
    db.commit()


def get_request_by_id_db(db: Session, request_id: str, for_update: bool = False):
    query = db.query(AccountRequest).filter(AccountRequest.id == request_id)
    if for_update:
        query = query.with_for_update().populate_existing()
    return query.first()


def _with_users(db: Session, visible_roles):
    """(request, user, resolver username) rows for requests the caller may see."""
    resolver = aliased(User)
    return (
        db.query(AccountRequest, User, resolver.username)
        .join(User, User.id == AccountRequest.user_id)
        .outerjoin(resolver, resolver.id == AccountRequest.resolved_by)
        .filter(User.role.in_(visible_roles))
    )


def list_requests_db(db: Session, visible_roles, status: str, category: str = None, page: int = 1, per_page: int = 20):
    query = _with_users(db, visible_roles).filter(AccountRequest.status == status)
    if category:
        query = query.filter(AccountRequest.category == category)
    order = AccountRequest.last_requested_at.desc() if status == "open" else AccountRequest.resolved_at.desc()
    total = query.count()
    rows = query.order_by(order).offset((page - 1) * per_page).limit(per_page).all()
    return rows, total


def get_visible_request_db(db: Session, request_id: str, visible_roles):
    return _with_users(db, visible_roles).filter(AccountRequest.id == request_id).first()


def count_open_requests_db(db: Session, visible_roles) -> int:
    return (
        db.query(AccountRequest)
        .join(User, User.id == AccountRequest.user_id)
        .filter(User.role.in_(visible_roles), AccountRequest.status == "open")
        .count()
    )


def close_requests_db(db: Session, user_id: str, category: str, status: str, actor_id: str) -> int:
    """Close every open request of a category for a user. Commits with the caller."""
    return db.query(AccountRequest).filter(
        AccountRequest.user_id == user_id,
        AccountRequest.category == category,
        AccountRequest.status == "open",
    ).update(
        {"status": status, "resolved_at": datetime.utcnow(), "resolved_by": actor_id},
        synchronize_session=False,
    )
