from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user, write_audit_log
from app.database.session import get_db
from app.models.profile_api_model import ProfileResponse, ProfileUpsertRequest
from app.models.profile_db_model import Profile
from app.models.user_db_model import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id, given_name="", family_name="")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/me", response_model=ProfileResponse)
def upsert_my_profile(
    payload: ProfileUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile.given_name = payload.given_name
    profile.family_name = payload.family_name
    profile.nick_name = payload.nick_name
    profile.picture_url = payload.picture_url
    profile.locale = payload.locale
    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    write_audit_log(db, actor_user_id=current_user.id, action="upsert_profile", target_type="profile", target_id=current_user.id)
    return profile
