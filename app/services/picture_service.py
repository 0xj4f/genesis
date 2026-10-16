"""Profile picture upload, resize, and management."""

import io
import warnings
from uuid import uuid4
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.models.profile_db_model import Profile

from app.services.storage_service import get_storage_backend

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 400
MAX_IMAGE_PIXELS = 16_000_000

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

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    raise ValueError("Unsupported image format")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image dimensions too large")
                source.load()
                img = source.convert("RGB")
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=85)
            return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=400, detail="Invalid image or image dimensions too large")


async def upload_profile_picture(db: Session, user_id: str, file: UploadFile) -> dict:
    """Upload and process a profile picture. Returns {picture, picture_key}."""

    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Read file
    data = await file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB")

    # Validate magic bytes
    detected_type = _detect_content_type(data)
    if not detected_type or detected_type != file.content_type:
        raise HTTPException(status_code=400, detail="File does not appear to be a valid image")

    # Resize and convert to WebP
    processed = await run_in_threadpool(_resize_and_convert, data)

    profile = await run_in_threadpool(
        lambda: db.query(Profile).filter(Profile.user_id == user_id).with_for_update().populate_existing().first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    old_key = profile.picture_key

    # Build storage key (relative to UPLOAD_DIR)
    file_id = str(uuid4())
    key = f"avatars/{user_id}/{file_id}.webp"

    # Upload
    storage = get_storage_backend()
    url = await storage.upload(key, processed, "image/webp")

    # Update profile
    profile.picture = url
    profile.picture_key = key
    profile.picture_updated_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            await storage.delete(key)
        except Exception:
            pass
        raise
    db.refresh(profile)
    if old_key:
        try:
            await storage.delete(old_key)
        except Exception:
            pass  # Best-effort cleanup after the database points at the new file.

    return {"picture": url, "picture_key": key}


async def delete_profile_picture(db: Session, user_id: str) -> None:
    """Delete a user's profile picture."""
    profile = await run_in_threadpool(
        lambda: db.query(Profile).filter(Profile.user_id == user_id).with_for_update().populate_existing().first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not profile.picture_key:
        raise HTTPException(status_code=400, detail="No profile picture to delete")

    old_key = profile.picture_key
    profile.picture = None
    profile.picture_key = None
    profile.picture_updated_at = datetime.utcnow()
    db.commit()
    try:
        await get_storage_backend().delete(old_key)
    except Exception:
        pass  # Best-effort cleanup after the transaction commits.
