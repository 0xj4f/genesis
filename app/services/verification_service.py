"""Optional email verification (EMAIL_VERIFY).

Links carry a random token in the URL fragment; only its SHA-256 is stored.
Each token is single-use, expires, and proves one specific address:
- purpose "verify": confirms the account's current email;
- purpose "change": applies a pending email change once the new address is proven.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.user_db_interface import get_user_by_email_db, get_user_by_id_db
from app.models.email_verification_db_model import EmailVerificationToken
from app.services.email_service import send_email
from app.utils.audit import security_event, subject_hash
from app.utils.security_store import get_security_store, SecurityStoreUnavailable

settings = get_settings()
logger = logging.getLogger(__name__)

RESEND_LIMIT_PER_HOUR = 3


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_token(db: Session, user, email: str, purpose: str) -> str:
    now = datetime.utcnow()
    # A new link replaces any earlier unused link for the same purpose.
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == str(user.id),
        EmailVerificationToken.purpose == purpose,
        EmailVerificationToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    raw_token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        user_id=str(user.id),
        token_hash=_token_hash(raw_token),
        email=email,
        purpose=purpose,
        expires_at=now + timedelta(hours=settings.EMAIL_VERIFY_TOKEN_TTL_HOURS),
    ))
    db.commit()
    return raw_token


def send_verification_email(db: Session, user, email: str = None, purpose: str = "verify") -> None:
    """Issue a link and email it. Delivery failures are logged, never raised:
    the user can request another link."""
    if not settings.EMAIL_VERIFY:
        return
    email = email or user.email
    raw_token = _issue_token(db, user, email, purpose)
    link = f"{settings.frontend_url}/verify-email#token={raw_token}"
    if purpose == "change":
        subject = "Confirm your new Genesis email address"
        intro = "Confirm this address to finish changing the email on your Genesis account."
    else:
        subject = "Verify your Genesis email address"
        intro = "Confirm this address to finish setting up your Genesis account."
    hours = settings.EMAIL_VERIFY_TOKEN_TTL_HOURS
    body = (
        f"Hello {user.username},\n\n{intro}\n\n{link}\n\n"
        f"The link expires in {hours} hours and can be used once. "
        "If you did not request this, you can ignore this email.\n"
    )
    try:
        send_email(email, subject, body)
        security_event("verification_email_sent", user_id=str(user.id), purpose=purpose)
    except Exception:
        logger.exception("Failed to send verification email for user %s", user.id)


def verify_email_token(db: Session, raw_token: str):
    """Consume a link. Returns the updated user or raises 400."""
    invalid = HTTPException(status_code=400, detail="Invalid or expired verification link")
    now = datetime.utcnow()
    token_hash = _token_hash(raw_token)
    # Atomic single-use claim.
    claimed = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash,
        EmailVerificationToken.used_at.is_(None),
        EmailVerificationToken.expires_at > now,
    ).update({"used_at": now}, synchronize_session=False)
    db.commit()
    if claimed != 1:
        raise invalid
    token = db.query(EmailVerificationToken).filter(EmailVerificationToken.token_hash == token_hash).first()
    user = get_user_by_id_db(db, token.user_id, for_update=True)
    if not user or user.disabled or not user.is_active:
        raise invalid

    if token.purpose == "change":
        user.email = token.email
    elif token.email != user.email:
        # The account's email changed after this link was sent.
        raise invalid
    user.email_verified = True
    user.email_verified_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
    security_event("email_verified", user_id=str(user.id), purpose=token.purpose)
    return user


def resend_verification(db: Session, email: str) -> None:
    """Send a fresh link if this address belongs to an unverified account.
    Callers always answer the same way so accounts are not revealed."""
    if not settings.EMAIL_VERIFY:
        return
    try:
        if get_security_store().check_rate(f"resend:{subject_hash(email)}", RESEND_LIMIT_PER_HOUR, 3600):
            return
    except SecurityStoreUnavailable:
        return
    user = get_user_by_email_db(db, email)
    if user and not user.email_verified and not user.disabled and user.is_active:
        send_verification_email(db, user)


def has_pending_email_change(db: Session, user) -> bool:
    return db.query(EmailVerificationToken.id).filter(
        EmailVerificationToken.user_id == str(user.id),
        EmailVerificationToken.purpose == "change",
        EmailVerificationToken.used_at.is_(None),
        EmailVerificationToken.expires_at > datetime.utcnow(),
    ).first() is not None
