from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes.users import router as user_router
from app.routes.profiles import router as profile_router
from app.routes.auth import router as auth_router
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
