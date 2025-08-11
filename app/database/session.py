from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os

DATABASE_USER = os.getenv("MYSQL_DEV_USER", "dev_project")
DATABASE_PASSWORD = os.getenv("MYSQL_DEV_PASSWORD", "SECURE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME", "genesis")
encoded_password = quote_plus(DATABASE_PASSWORD)  # if password has special characters

# Construct the database URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{encoded_password}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

print(SQLALCHEMY_DATABASE_URL)
# Create the engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()