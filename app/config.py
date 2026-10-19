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
    # HS256 signing secret, used only outside production when no RSA key pair is
    # configured. No default: a committed secret would let anyone forge tokens.
    OAUTH_SECRET_KEY: Optional[SecretStr] = None

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

    # Password hashing: Argon2id via pwdlib. bcrypt hashes from before the
    # migration still verify and are replaced on the next successful login.
    # "bcrypt" keeps writing bcrypt (reads both) for a staged rollout.
    PASSWORD_HASH_SCHEME: Literal["argon2id", "bcrypt"] = "argon2id"
    # OWASP minimum (19 MiB, t=2, p=1); see backend.md for the benchmark.
    PASSWORD_ARGON2_MEMORY_KIB: int = Field(19456, ge=7168, le=262144)
    PASSWORD_ARGON2_TIME_COST: int = Field(2, ge=1, le=10)
    PASSWORD_ARGON2_PARALLELISM: int = Field(1, ge=1, le=8)
    # Caps simultaneous hashes so memory stays bounded (4 x 19 MiB by default).
    PASSWORD_HASH_CONCURRENCY: int = Field(4, ge=1, le=64)

    # Per-account login throttling (in-process, like the per-IP limits)
    LOGIN_MAX_FAILURES: int = Field(5, ge=1, le=100)
    LOGIN_FAILURE_WINDOW_SECONDS: int = Field(900, ge=60, le=86400)
    LOGIN_LOCKOUT_MAX_SECONDS: int = Field(900, ge=60, le=86400)

    # SSO-only accounts (no password) must have signed in this recently to set
    # a first password or change their email.
    REAUTH_MAX_AGE_SECONDS: int = Field(600, ge=60, le=3600)

    # Base URL of the Genesis web app. Used for the SSO hand-off redirect, email
    # links and the OAuth consent page. Optional: without it SSO callbacks
    # return JSON and email verification cannot be enabled.
    FRONTEND_URL: Optional[str] = None

    # Email verification is optional so Genesis runs without any mail service.
    EMAIL_VERIFY: bool = False
    EMAIL_BACKEND: Literal["smtp", "console"] = "console"
    EMAIL_FROM: Optional[str] = None
    EMAIL_VERIFY_TOKEN_TTL_HOURS: int = Field(24, ge=1, le=168)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = Field(587, ge=1, le=65535)
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None
    SMTP_SECURITY: Literal["starttls", "tls", "none"] = "starttls"
    SMTP_TIMEOUT_SECONDS: int = Field(10, ge=1, le=60)

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
    def validate_frontend_and_email(self):
        if self.FRONTEND_URL:
            url = urlsplit(self.FRONTEND_URL)
            if (url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password
                    or url.query or url.fragment):
                raise ValueError("FRONTEND_URL must be an absolute HTTP(S) URL without credentials, query or fragment")
            if self.ENVIRONMENT == "production" and url.scheme != "https":
                raise ValueError("Production FRONTEND_URL must use HTTPS")
        if self.EMAIL_VERIFY:
            if not self.FRONTEND_URL or not self.EMAIL_FROM:
                raise ValueError("EMAIL_VERIFY=true requires FRONTEND_URL and EMAIL_FROM")
            if self.EMAIL_BACKEND == "smtp" and not self.SMTP_HOST:
                raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST")
            if self.ENVIRONMENT == "production":
                if self.EMAIL_BACKEND != "smtp":
                    raise ValueError("Production email verification requires EMAIL_BACKEND=smtp")
                if self.SMTP_SECURITY == "none":
                    raise ValueError("Production SMTP requires SMTP_SECURITY=starttls or tls")
        return self

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
    def frontend_url(self) -> Optional[str]:
        return self.FRONTEND_URL.rstrip("/") if self.FRONTEND_URL else None

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
