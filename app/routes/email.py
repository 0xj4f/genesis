"""Public auth configuration and optional email verification endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.oauth_providers import list_providers
from app.config import get_settings
from app.database.session import get_db
from app.models.user_api_model import EmailResendRequest, EmailVerifyRequest
from app.services.verification_service import resend_verification, verify_email_token

router = APIRouter()
settings = get_settings()


@router.get("/auth/config", tags=["auth"])
def auth_config():
    """What the web app needs to render sign-up and sign-in screens."""
    return {"email_verification": settings.EMAIL_VERIFY, "sso_providers": list_providers()}


@router.post("/auth/email/verify", tags=["auth"])
def verify_email(body: EmailVerifyRequest, db: Session = Depends(get_db)):
    """Consume a verification link (single use, expires)."""
    user = verify_email_token(db, body.token)
    return {"message": "Email verified", "email": user.email}


@router.post("/auth/email/resend", tags=["auth"], status_code=202)
def resend_verification_email(body: EmailResendRequest, db: Session = Depends(get_db)):
    """Always answers the same way so it cannot be used to discover accounts."""
    resend_verification(db, body.email)
    return JSONResponse(
        {"message": "If this address needs verification, a new link has been sent."}, status_code=202
    )
