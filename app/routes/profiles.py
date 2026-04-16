from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.profile_service import (
    create_profile_service,
    get_profile_by_user_service,
    update_profile_service,
    delete_profile_service,
)
from app.services.picture_service import upload_profile_picture, delete_profile_picture
from app.models.profile_api_model import ProfileCreate, Profile, ProfileUpdate, PictureUploadResponse
from app.models.user_api_model import User
from app.auth.auth import oauth_authenticate_current_user

router = APIRouter()


@router.post("/", response_model=Profile)
def create_profile(
    profile_create: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    profile_create.user_id = current_user.id
    profile_create.email = current_user.email
    return create_profile_service(db, profile_create)


@router.get("/me/", response_model=Profile)
def get_own_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    return get_profile_by_user_service(db, current_user.id)


@router.put("/me/", response_model=Profile)
def update_own_profile(
    profile_update: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    return update_profile_service(db, current_user.id, profile_update)


@router.delete("/me/", response_model=dict)
def delete_own_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    if delete_profile_service(db, current_user.id):
        return {"message": f"Profile with user ID {current_user.id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")


# ---- Picture Upload/Delete ----

@router.post("/me/picture", response_model=PictureUploadResponse)
async def upload_picture(
    picture: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    return await upload_profile_picture(db, str(current_user.id), picture)


@router.delete("/me/picture")
async def delete_picture(
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth_authenticate_current_user),
):
    await delete_profile_picture(db, str(current_user.id))
    return {"message": "Profile picture deleted"}
