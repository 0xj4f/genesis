from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    MYSQL_DEV_USER: str = "dev_project"
    MYSQL_DEV_PASSWORD: str = "SECURE_PASSWORD"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_NAME: str = "genesis"

    # OAuth / JWT Core
    OAUTH_ISSUER: str = "https://auth.local"
    OAUTH_ALGORITHM: str = "RS256"
    OAUTH_DEFAULT_AUDIENCE: str = "genesis-api"
    OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OAUTH_REFRESH_TOKEN_TTL_DAYS: int = 30
    OAUTH_SECRET_KEY: str = "0f2883258b3c2cb9e21f1bdc827eafb9b7ad5509bf37103f82a1abab9109c65a"

    # RS256 Key Paths (file-based, for dev/simple deployments)
    OAUTH_PRIVATE_KEY_PATH: Optional[str] = None
    OAUTH_PUBLIC_KEY_PATH: Optional[str] = None
    OAUTH_JWT_KID: str = "genesis-dev-1"

    # JWKS
    JWKS_CACHE_TTL_SECONDS: int = 300

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:8080"

    # Sessions
    MAX_CONCURRENT_SESSIONS: int = 5

    # SSO Providers (future - Phase 5)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: Optional[str] = None
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_REDIRECT_URI: Optional[str] = None

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    UPLOAD_DIR: str = "./uploads"
    S3_BUCKET: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        password = quote_plus(self.MYSQL_DEV_PASSWORD)
        return (
            f"mysql+pymysql://{self.MYSQL_DEV_USER}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
