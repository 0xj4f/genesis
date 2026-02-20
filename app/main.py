import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.auth import bootstrap_root_admin
from app.database.session import Base, SessionLocal, engine
from app.routes.admin import router as admin_ops_router
from app.routes.auth import router as auth_router
from app.routes.profiles import router as profile_router
from app.routes.users import admin_router as admin_user_router
from app.routes.users import user_router

app = FastAPI(title="Genesis - IAM MVP")

cors_origins = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup_event():
    logger.info("Creating database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_root_admin(db)
    finally:
        db.close()
    logger.info("Schema ready and root admin bootstrap checked.")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(admin_user_router)
app.include_router(admin_ops_router)
