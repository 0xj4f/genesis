"""Admin routes: login, analytics, user management, OAuth client management."""

import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.auth.auth import require_admin, require_root
from app.database.oauth_client_db_interface import (
    create_oauth_client_db, get_oauth_client_by_id_db,
    get_oauth_client_by_name_db, get_all_oauth_clients_db, update_oauth_client_db,
)
from app.database.user_db_interface import get_user_by_id_db, delete_user_by_id_db
from app.models.oauth_client_api_model import (
    OAuthClientCreate, OAuthClientResponse, OAuthClientWithSecret, OAuthClientUpdate,
)
from app.models.admin_api_model import (
    AnalyticsResponse, AdminUserListResponse, AdminUserDetail, RoleUpdateRequest,
)
from app.models.user_api_model import Token
from app.services.admin_service import (
    admin_login_service, get_analytics, get_users_paginated,
    get_user_detail, update_user_role, toggle_user_status,
)
from app.utils.security import hash_password

router = APIRouter()


# ---- Admin Login ----

@router.post("/admin/login", tags=["admin"], response_model=Token)
def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Admin-specific login. Rejects non-admin/root users."""
    return admin_login_service(db, form_data.username, form_data.password, request)


# ---- Analytics ----

@router.get("/admin/analytics", tags=["admin"], response_model=AnalyticsResponse)
def analytics(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    return get_analytics(db)


# ---- User Management ----

@router.get("/admin/users", tags=["admin"], response_model=AdminUserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_users_paginated(db, page, per_page, search)


@router.get("/admin/users/{user_id}", tags=["admin"], response_model=AdminUserDetail)
def get_user(user_id: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    return get_user_detail(db, user_id)


@router.post("/admin/users/{user_id}/role", tags=["admin"])
def change_role(
    user_id: str,
    body: RoleUpdateRequest,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return update_user_role(db, user_id, body.role, current_user.role)


@router.post("/admin/users/{user_id}/disable", tags=["admin"])
def disable_user(user_id: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    return toggle_user_status(db, user_id)


@router.delete("/admin/users/{user_id}", tags=["admin"])
def delete_user(user_id: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    user = get_user_by_id_db(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "root":
        raise HTTPException(status_code=403, detail="Cannot delete ROOT user")
    delete_user_by_id_db(db, user_id)
    return {"message": "User deleted"}


# ---- OAuth Client Management ----

@router.post("/admin/clients", tags=["admin"], response_model=OAuthClientWithSecret)
def create_client(client_data: OAuthClientCreate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    existing = get_oauth_client_by_name_db(db, client_data.client_name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Client '{client_data.client_name}' already exists")
    client_secret = secrets.token_urlsafe(32)
    client = create_oauth_client_db(db, {
        "client_secret_hash": hash_password(client_secret),
        "client_name": client_data.client_name,
        "redirect_uris": client_data.redirect_uris,
        "allowed_scopes": client_data.allowed_scopes,
        "allowed_audiences": client_data.allowed_audiences,
        "grant_types": client_data.grant_types,
        "is_active": True,
        "is_confidential": client_data.is_confidential,
    })
    return OAuthClientWithSecret(
        id=client.id, client_name=client.client_name, client_secret=client_secret,
        redirect_uris=client.redirect_uris, allowed_scopes=client.allowed_scopes,
        allowed_audiences=client.allowed_audiences, grant_types=client.grant_types,
        is_active=client.is_active, is_confidential=client.is_confidential, created_at=client.created_at,
    )


@router.get("/admin/clients", tags=["admin"], response_model=list[OAuthClientResponse])
def list_clients(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return get_all_oauth_clients_db(db)


@router.get("/admin/clients/{client_id}", tags=["admin"], response_model=OAuthClientResponse)
def get_client(client_id: str, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/admin/clients/{client_id}", tags=["admin"], response_model=OAuthClientResponse)
def update_client(client_id: str, update_data: OAuthClientUpdate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    client = update_oauth_client_db(db, client_id, update_data.model_dump(exclude_unset=True))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/admin/clients/{client_id}/rotate-secret", tags=["admin"])
def rotate_secret(client_id: str, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    new_secret = secrets.token_urlsafe(32)
    client = update_oauth_client_db(db, client_id, {"client_secret_hash": hash_password(new_secret)})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client_id": client.id, "client_name": client.client_name, "client_secret": new_secret, "message": "Secret rotated."}
