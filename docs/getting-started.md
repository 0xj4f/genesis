# Getting Started

## Prerequisites

- Docker and Docker Compose
- curl (for testing)

## Run with Docker Compose

```bash
git clone <repo-url> genesis
cd genesis

# Start the stack (MySQL + API)
docker compose up -d

# Check logs
docker compose logs -f api
```

The API starts on **port 8001** (mapped from container port 8000). MySQL runs on port 3306.

On first start, the entrypoint script:
1. Generates RSA key pair (if not present in `./secrets/`)
2. Runs Alembic migrations (creates all 7 tables)
3. Starts the FastAPI server

### Verify it's running

```bash
# JWKS endpoint (no auth required)
curl http://localhost:8001/.well-known/jwks.json

# OIDC discovery
curl http://localhost:8001/.well-known/openid-configuration

# Swagger UI
open http://localhost:8001/docs
```

## Environment Variables

All configuration is via environment variables. Set them in `docker-compose.yml` or a `.env` file.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `MYSQL_DEV_USER` | `dev_project` | MySQL username |
| `MYSQL_DEV_PASSWORD` | `SECURE_PASSWORD` | MySQL password |
| `DATABASE_HOST` | `localhost` | MySQL host (`db` in Docker) |
| `DATABASE_PORT` | `3306` | MySQL port |
| `DATABASE_NAME` | `genesis` | Database name |

### JWT / Auth

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_ISSUER` | `https://auth.local` | Token issuer (`iss` claim). Set to your public URL in production |
| `OAUTH_ALGORITHM` | `RS256` | Signing algorithm |
| `OAUTH_DEFAULT_AUDIENCE` | `genesis-api` | Default `aud` claim |
| `OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `OAUTH_REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh token TTL |
| `OAUTH_SECRET_KEY` | (dev default) | HS256 fallback key. Change in production |
| `OAUTH_PRIVATE_KEY_PATH` | (none) | Path to RSA private key PEM |
| `OAUTH_PUBLIC_KEY_PATH` | (none) | Path to RSA public key PEM |
| `OAUTH_JWT_KID` | `genesis-dev-1` | Key ID for JWKS |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ALLOW_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |

### Sessions

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_SESSIONS` | `5` | Max active sessions per user |

### SSO Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | (none) | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | (none) | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | (none) | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | (none) | GitHub OAuth client secret |
| `FACEBOOK_CLIENT_ID` | (none) | Facebook App ID |
| `FACEBOOK_CLIENT_SECRET` | (none) | Facebook App Secret |

See [SSO Setup Guides](sso/README.md) for how to obtain these credentials.

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `UPLOAD_DIR` | `./uploads` | Local upload directory |
| `S3_BUCKET` | (none) | S3 bucket name |
| `S3_REGION` | (none) | AWS region |
| `S3_ENDPOINT_URL` | (none) | Custom S3 endpoint (MinIO) |

## Local Development (without Docker)

```bash
# Python 3.13+
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# MySQL must be running locally
# Create database: CREATE DATABASE genesis;

# Generate RSA keys
python -m app.cli generate-keys

# Configure
cp .env.example .env
# Edit .env with your MySQL credentials and key paths

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

## CLI Commands

```bash
# Generate RSA key pair
python -m app.cli generate-keys [--output-dir ./secrets] [--key-size 2048] [--force]

# Register an OAuth client
python -m app.cli create-client my-app \
  --redirect-uris "http://localhost:3000/callback" \
  --scopes "openid,profile,email,offline_access" \
  --audiences "genesis-api" \
  --grant-types "authorization_code,refresh_token"

# Rotate signing keys (planned)
python -m app.cli rotate-keys
```
