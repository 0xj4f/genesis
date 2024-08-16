from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from app.routes.users import router as user_router
from app.routes.auth import router as auth_router

app = FastAPI(title="Genesis - Identity Access Management")

# Include routers
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(auth_router, prefix="", tags=["auth"])