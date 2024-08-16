# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.database.session import get_db
# from app.services.profile_service import (
#     create_profile_service,
#     get_profiles_service,
#     get_profile_by_id_service,
#     update_profile_service,
#     delete_profile_service,
# )
# from app.models.profile_api_model import ProfileCreate, Profile, ProfileUpdate

# router = APIRouter()

# @router.post("/", response_model=Profile)
# def create_profile(profile_create: ProfileCreate, db: Session = Depends(get_db)):
#     return create_profile_service(db, profile_create)

# @router.get("/", response_model=list[Profile])
# def get_profiles(db: Session = Depends(get_db)):
#     return get_profiles_service(db)

# @router.get("/{profile_id}", response_model=Profile)
# def get_profile_by_id(profile_id: int, db: Session = Depends(get_db)):
#     profile = get_profile_by_id_service(db, profile_id)
#     if not profile:
#         raise HTTPException(status_code=404, detail="Profile not found")
#     return profile

# @router.put("/{profile_id}", response_model=Profile)
# def update_profile(profile_id: int, profile_update: ProfileUpdate, db: Session = Depends(get_db)):
#     return update_profile_service(db, profile_id, profile_update)

# @router.delete("/{profile_id}", response_model=dict)
# def delete_profile(profile_id: int, db: Session = Depends(get_db)):
#     if delete_profile_service(db, profile_id):
#         return {"message": f"Profile with ID {profile_id} has been successfully deleted"}
#     else:
#         raise HTTPException(status_code=404, detail="Profile not found")

# ./app/routes/profiles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.profile_service import (
    create_profile_service,
    get_profile_by_user_service,
    update_profile_service,
    delete_profile_service,
)
from app.models.profile_api_model import ProfileCreate, Profile, ProfileUpdate
from app.models.user_api_model import User
from app.auth.auth import oauth_authenticate_current_user

router = APIRouter()

@router.post("/", response_model=Profile)
def create_profile(profile_create: ProfileCreate, db: Session = Depends(get_db), current_user: User = Depends(oauth_authenticate_current_user)):
    profile_create.user_id = current_user.id  # Set the user_id to the current user's ID
    profile_create.email = current_user.email
    return create_profile_service(db, profile_create)

@router.get("/me/", response_model=Profile)
def get_own_profile(db: Session = Depends(get_db), current_user: User = Depends(oauth_authenticate_current_user)):
    return get_profile_by_user_service(db, current_user.id)

@router.put("/me/", response_model=Profile)
def update_own_profile(profile_update: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(oauth_authenticate_current_user)):
    return update_profile_service(db, current_user.id, profile_update)

@router.delete("/me/", response_model=dict)
def delete_own_profile(db: Session = Depends(get_db), current_user: User = Depends(oauth_authenticate_current_user)):
    if delete_profile_service(db, current_user.id):
        return {"message": f"Profile with user ID {current_user.id} has been successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")

