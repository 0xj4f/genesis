from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr, model_validator
from urllib.parse import urlsplit


class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    ALLOWED_HOSTS: str = "*"
    RATE_LIMIT_PER_SECOND: int = Field(30, ge=1, le=10000)
    AUTH_RATE_LIMIT_PER_MINUTE: int = Field(10, ge=1, le=10000)
    REFRESH_RATE_LIMIT_PER_MINUTE: int = Field(60, ge=1, le=10000)
    MAX_REQUEST_BODY_BYTES: int = Field(6 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    BOOTSTRAP_ROOT_PASSWORD: Optional[SecretStr] = None

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
    MAX_CONCURRENT_SESSIONS: int = Field(5, ge=1, le=100)

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

    @model_validator(mode="after")
    def validate_production(self):
        if self.ENVIRONMENT == "production":
            if self.OAUTH_ALGORITHM != "RS256" or not (self.OAUTH_PRIVATE_KEY_PATH and self.OAUTH_PUBLIC_KEY_PATH):
                raise ValueError("Production requires RS256 private and public key paths")
            issuer = urlsplit(self.OAUTH_ISSUER)
            if (issuer.scheme != "https" or not issuer.netloc or issuer.username or issuer.password
                    or issuer.query or issuer.fragment):
                raise ValueError("Production OAUTH_ISSUER must be an absolute HTTPS URL without credentials, query or fragment")
            if not self.allowed_hosts or any("*" in host for host in self.allowed_hosts):
                raise ValueError("Production requires explicit ALLOWED_HOSTS")
            if not self.cors_origins or any(
                urlsplit(origin).scheme != "https" or "*" in origin
                or not urlsplit(origin).netloc or urlsplit(origin).path
                or urlsplit(origin).query or urlsplit(origin).fragment
                for origin in self.cors_origins
            ):
                raise ValueError("Production CORS origins must be explicit HTTPS origins without paths")
        return self

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

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
