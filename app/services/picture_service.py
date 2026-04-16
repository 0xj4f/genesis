"""Profile picture upload, resize, and management."""

import io
from uuid import uuid4
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.profile_db_interface import get_profile_by_user_db
from app.services.storage_service import get_storage_backend

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 400

# Magic bytes for image format detection
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF
    b"GIF8": "image/gif",
}


def _detect_content_type(data: bytes) -> str | None:
    for magic, ctype in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            return ctype
    return None


def _resize_and_convert(data: bytes, max_dim: int = MAX_DIMENSION) -> bytes:
    """Resize image to max_dim x max_dim and convert to WebP."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))

    # Convert RGBA/P to RGB for WebP
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize maintaining aspect ratio
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="WEBP", quality=85)
    return output.getvalue()


async def upload_profile_picture(db: Session, user_id: str, file: UploadFile) -> dict:
    """Upload and process a profile picture. Returns {picture, picture_key}."""

    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Read file
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB")

    # Validate magic bytes
    detected_type = _detect_content_type(data)
    if not detected_type:
        raise HTTPException(status_code=400, detail="File does not appear to be a valid image")

    # Resize and convert to WebP
    processed = _resize_and_convert(data)

    # Build storage key (relative to UPLOAD_DIR)
    file_id = str(uuid4())
    key = f"avatars/{user_id}/{file_id}.webp"

    # Upload
    storage = get_storage_backend()
    url = await storage.upload(key, processed, "image/webp")

    # Delete old picture if exists
    profile = get_profile_by_user_db(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if profile.picture_key:
        try:
            await storage.delete(profile.picture_key)
        except Exception:
            pass  # Best-effort cleanup

    # Update profile
    profile.picture = url
    profile.picture_key = key
    profile.picture_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return {"picture": url, "picture_key": key}


async def delete_profile_picture(db: Session, user_id: str) -> None:
    """Delete a user's profile picture."""
    profile = get_profile_by_user_db(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not profile.picture_key:
        raise HTTPException(status_code=400, detail="No profile picture to delete")

    storage = get_storage_backend()
    try:
        await storage.delete(profile.picture_key)
    except Exception:
        pass  # Best-effort

    profile.picture = None
    profile.picture_key = None
    profile.picture_updated_at = datetime.utcnow()
    db.commit()
