from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.auth import get_current_root_admin, write_audit_log
from app.database.session import get_db
from app.models.user_api_model import AuditLogItem, SessionItem
from app.models.user_db_model import AuditLog, Session as UserSession, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sessions", response_model=list[SessionItem])
def list_sessions(_: User = Depends(get_current_root_admin), db: Session = Depends(get_db)):
    return db.query(UserSession).all()


@router.post("/sessions/{session_id}/revoke", response_model=dict)
def revoke_session(
    session_id: str,
    root_admin: User = Depends(get_current_root_admin),
    db: Session = Depends(get_db),
):
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.revoked_at = datetime.utcnow()
    session.revoked_reason = "admin_revoke"
    db.commit()

    write_audit_log(
        db,
        actor_user_id=root_admin.id,
        action="admin_revoke_session",
        target_type="session",
        target_id=session_id,
    )
    return {"message": "session_revoked"}


@router.get("/audit-logs", response_model=list[AuditLogItem])
def list_audit_logs(_: User = Depends(get_current_root_admin), db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()
