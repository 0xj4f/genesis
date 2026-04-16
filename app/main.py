import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.routes.users import router as user_router
from app.routes.profiles import router as profile_router
from app.routes.auth import router as auth_router
from app.routes.sso import router as sso_router
from app.routes.oidc import router as oidc_router
from app.routes.admin import router as admin_router
import logging

settings = get_settings()

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="Genesis - Identity Access Management")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router, prefix="", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(sso_router, prefix="", tags=["sso"])
app.include_router(oidc_router, prefix="", tags=["oidc"])
app.include_router(admin_router, prefix="", tags=["admin"])

# Serve uploaded avatars as static files (local storage backend)
avatars_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
os.makedirs(avatars_dir, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=avatars_dir), name="avatars")
