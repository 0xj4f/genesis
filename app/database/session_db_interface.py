from sqlalchemy.orm import Session as DBSession
from app.models.session_db_model import Session
from datetime import datetime


def create_session_db(db: DBSession, session_data: dict) -> Session:
    db_session = Session(**session_data)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_session_by_id_db(db: DBSession, session_id: str) -> Session | None:
    return db.query(Session).filter(Session.id == session_id).first()


def get_session_by_jti_db(db: DBSession, jti: str) -> Session | None:
    return db.query(Session).filter(
        Session.refresh_token_jti == jti,
        Session.is_active == True,  # noqa: E712
    ).first()


def get_active_sessions_by_user_db(db: DBSession, user_id: str) -> list[Session]:
    return db.query(Session).filter(
        Session.user_id == user_id,
        Session.is_active == True,  # noqa: E712
    ).order_by(Session.created_at.desc()).all()


def update_session_jti_db(db: DBSession, session_id: str, new_jti: str) -> Session | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return None
    session.refresh_token_jti = new_jti
    session.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def revoke_session_db(db: DBSession, session_id: str, reason: str = "user_logout") -> Session | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return None
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = reason
    db.commit()
    db.refresh(session)
    return session


def revoke_all_user_sessions_db(
    db: DBSession, user_id: str, except_session_id: str | None = None, reason: str = "user_logout"
) -> int:
    query = db.query(Session).filter(
        Session.user_id == user_id,
        Session.is_active == True,  # noqa: E712
    )
    if except_session_id:
        query = query.filter(Session.id != except_session_id)

    now = datetime.utcnow()
    count = query.update(
        {"is_active": False, "revoked_at": now, "revoked_reason": reason},
        synchronize_session="fetch",
    )
    db.commit()
    return count


def count_active_sessions_db(db: DBSession, user_id: str) -> int:
    return db.query(Session).filter(
        Session.user_id == user_id,
        Session.is_active == True,  # noqa: E712
    ).count()


def get_oldest_active_session_db(db: DBSession, user_id: str) -> Session | None:
    return db.query(Session).filter(
        Session.user_id == user_id,
        Session.is_active == True,  # noqa: E712
    ).order_by(Session.created_at.asc()).first()
