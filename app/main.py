from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.declarative import declarative_base
from app.routes.users import router as user_router
from app.routes.profiles import router as profile_router
from app.routes.auth import router as auth_router
from app.database.session import Base,engine
import logging

app = FastAPI(title="Genesis - Identity Access Management")

# origins = ["http://localhost:8080", "http://127.0.0.1:8000"]
# ONLY FOR TEST PUPRPOSES
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # or specify ["GET", "POST", ...]
    allow_headers=["*"],  # or specify ["Content-Type", "Authorization", ...]
)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Log the creation of tables
logger.info("Creating tables...")
Base.metadata.create_all(bind=engine)
logger.info("Tables created.")

# Include routers
app.include_router(auth_router, prefix="", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])