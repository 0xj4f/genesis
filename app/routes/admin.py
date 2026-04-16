"""Admin routes for managing OAuth clients and system configuration."""

import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.auth.auth import oauth_authenticate_current_user
from app.database.oauth_client_db_interface import (
    create_oauth_client_db,
    get_oauth_client_by_id_db,
    get_oauth_client_by_name_db,
    get_all_oauth_clients_db,
    update_oauth_client_db,
)
from app.models.oauth_client_api_model import (
    OAuthClientCreate,
    OAuthClientResponse,
    OAuthClientWithSecret,
    OAuthClientUpdate,
)
from app.utils.security import hash_password

router = APIRouter()


@router.post("/admin/clients", tags=["admin"], response_model=OAuthClientWithSecret)
def create_client(
    client_data: OAuthClientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """Register a new OAuth client. Returns client_id and client_secret (one-time)."""
    existing = get_oauth_client_by_name_db(db, client_data.client_name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Client '{client_data.client_name}' already exists")

    client_secret = secrets.token_urlsafe(32)
    client_secret_hash = hash_password(client_secret)

    client = create_oauth_client_db(db, {
        "client_secret_hash": client_secret_hash,
        "client_name": client_data.client_name,
        "redirect_uris": client_data.redirect_uris,
        "allowed_scopes": client_data.allowed_scopes,
        "allowed_audiences": client_data.allowed_audiences,
        "grant_types": client_data.grant_types,
        "is_active": True,
        "is_confidential": client_data.is_confidential,
    })

    return OAuthClientWithSecret(
        id=client.id,
        client_name=client.client_name,
        client_secret=client_secret,
        redirect_uris=client.redirect_uris,
        allowed_scopes=client.allowed_scopes,
        allowed_audiences=client.allowed_audiences,
        grant_types=client.grant_types,
        is_active=client.is_active,
        is_confidential=client.is_confidential,
        created_at=client.created_at,
    )


@router.get("/admin/clients", tags=["admin"], response_model=list[OAuthClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """List all registered OAuth clients."""
    return get_all_oauth_clients_db(db)


@router.get("/admin/clients/{client_id}", tags=["admin"], response_model=OAuthClientResponse)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """Get details of a specific OAuth client."""
    client = get_oauth_client_by_id_db(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/admin/clients/{client_id}", tags=["admin"], response_model=OAuthClientResponse)
def update_client(
    client_id: str,
    update_data: OAuthClientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """Update an OAuth client's configuration."""
    client = update_oauth_client_db(db, client_id, update_data.model_dump(exclude_unset=True))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/admin/clients/{client_id}/rotate-secret", tags=["admin"])
def rotate_client_secret(
    client_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth_authenticate_current_user),
):
    """Rotate a client's secret. Returns the new secret (one-time)."""
    new_secret = secrets.token_urlsafe(32)
    new_hash = hash_password(new_secret)
    client = update_oauth_client_db(db, client_id, {"client_secret_hash": new_hash})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "client_id": client.id,
        "client_name": client.client_name,
        "client_secret": new_secret,
        "message": "Secret rotated. Save the new secret now.",
    }
