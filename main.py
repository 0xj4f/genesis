# from fastapi import FastAPI, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from database_config import SessionLocal, engine
# from models import Base
# from database_interface import (
#     create_user,
#     get_users,
#     get_user_by_id,
#     update_user,
#     delete_user,
# )
#
# from uuid import UUID
#
# app = FastAPI()
#
#
# # Dependency to get the database session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
#
# @app.get("/")
# def read_root():
#     return {"Hello": "World"}
#
#
# # Create User Endpoint
# @app.post("/create_user/")
# def api_create_user(
#     username: str, email: str, password: str, db: Session = Depends(get_db)
# ):
#     db_user = create_user(db, username=username, email=email, hashed_password=password)
#     return db_user
#
#
# # Get All Users Endpoint
# @app.get("/get_users/")
# def api_get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     return get_users(db, skip=skip, limit=limit)
#
#
# # Get User by ID Endpoint
# @app.get("/get_user/{user_id}")
# def api_get_user(user_id: UUID, db: Session = Depends(get_db)):
#     db_user = get_user_by_id(db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user
#
#
# # Update User by ID Endpoint
# @app.put("/update_user/{user_id}")
# def api_update_user(
#     user_id: UUID,
#     username: str = None,
#     email: str = None,
#     password: str = None,
#     db: Session = Depends(get_db),
# ):
#     db_user = update_user(
#         db, user_id=user_id, username=username, email=email, hashed_password=password
#     )
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user
#
#
# # Delete User by ID Endpoint
# @app.delete("/delete_user/{user_id}")
# def api_delete_user(user_id: UUID, db: Session = Depends(get_db)):
#     db_user = delete_user(db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database_config import SessionLocal, engine
from database_models import Base
from database_interface import (
    create_user,
    get_all_users,
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
)

from api_models import UserCreate, User, UserSearchRequest


app = FastAPI()

# Create the database tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=User)
def create_user_endpoint(user_create: UserCreate, db: Session = Depends(get_db)):
    # Validate if the email already exists
    if get_user_by_email(db, email=user_create.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate if the username already exists
    if get_user_by_username(db, username=user_create.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create and return the new user
    db_user = create_user(db=db, user_create=user_create)
    return db_user


@app.get("/users/", response_model=list[User])
def get_users_endpoint(db: Session = Depends(get_db)):
    users = get_all_users(db)
    return users


@app.get("/users/{user_id}", response_model=User)
def get_user_by_id_endpoint(user_id: str, db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/search", response_model=User)
async def get_user_by_request(
    request: UserSearchRequest, db: Session = Depends(get_db)
):
    if request.email:
        user = get_user_by_email(db, email=request.email)
        if user:
            return user
        raise HTTPException(
            status_code=404, detail="User with the provided email not found"
        )

    if request.username:
        user = get_user_by_username(db, username=request.username)
        if user:
            return user
        raise HTTPException(
            status_code=404, detail="User with the provided username not found"
        )

    raise HTTPException(
        status_code=400, detail="Either email or username must be provided"
    )
