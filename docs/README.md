# Genesis - Identity Access Management

Genesis is a production-grade IAM microservice built with FastAPI. It provides a single authentication backend for all your projects -- ecommerce, payment gateways, internal tools, or any JWT-native web application.

## Features

| Feature | Description |
|---------|-------------|
| **Native Auth** | Username/password registration and login with bcrypt hashing |
| **RS256 JWT** | Asymmetric token signing with key rotation support |
| **JWKS Endpoint** | `/.well-known/jwks.json` for downstream token verification |
| **Token Refresh** | Rotation with replay detection (revokes session on reuse) |
| **Session Management** | Server-side sessions with device tracking and concurrent limits |
| **SSO Login** | Google, GitHub, Facebook via OAuth2 Authorization Code flow |
| **Account Linking** | Link/unlink multiple SSO providers to one account |
| **OIDC Provider** | Full OpenID Connect provider for downstream apps |
| **Profile Management** | Name, locale, timezone with profile picture upload |
| **Avatar Upload** | Resize to WebP, pluggable storage (local filesystem or S3) |
| **Multi-Project** | OAuth client registration with audience/scope isolation |
| **Client Credentials** | Machine-to-machine authentication for services |
| **PKCE Support** | Proof Key for Code Exchange for public clients (SPAs) |
| **Docker Ready** | Docker Compose with MySQL, auto-migration, key generation |

## Architecture

```
Client (Browser/App/Service)
    |
    v
FastAPI Application (app/main.py)
    |
    +-- routes/        API endpoints (auth, users, profiles, sso, oidc, admin)
    +-- services/      Business logic (auth, session, sso, oidc, picture, storage)
    +-- auth/          JWT creation/validation, RS256 key management, OAuth providers
    +-- database/      SQLAlchemy interfaces for each table
    +-- models/        DB models (SQLAlchemy) + API models (Pydantic)
    +-- utils/         Password hashing, helpers
    +-- config.py      Centralized settings (Pydantic BaseSettings)
    |
    v
MySQL 8.0 (7 tables: users, profiles, sessions, oauth_accounts, oauth_clients, authorization_codes, jwk_keys)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | MySQL 8.0 + SQLAlchemy |
| Migrations | Alembic |
| JWT | python-jose (RS256/HS256) |
| Password Hashing | bcrypt |
| Image Processing | Pillow |
| HTTP Client | httpx (SSO provider calls) |
| Containerization | Docker + Docker Compose |

## Quickstart

```bash
# Clone and start
git clone <repo-url> genesis
cd genesis
docker compose up -d

# Verify it's running (port 8001)
curl http://localhost:8001/.well-known/jwks.json

# Create a user
curl -X POST http://localhost:8001/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "SecurePass123!"}'

# Login
curl -X POST http://localhost:8001/token \
  -d "username=admin&password=SecurePass123!"
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](getting-started.md) | Docker setup, environment variables, local development |
| [Native Auth Guide](native-auth-guide.md) | End-to-end: register, login, profile, sessions, refresh |
| [API Reference](api-reference.md) | All 33+ endpoints with curl examples |
| [OIDC Integration](oidc-guide.md) | How downstream apps authenticate via Genesis |
| [SSO Setup](sso/README.md) | Overview of Social Sign-On |
| [Google SSO](sso/google.md) | Step-by-step Google OAuth setup |
| [GitHub SSO](sso/github.md) | Step-by-step GitHub OAuth setup |
| [Facebook SSO](sso/facebook.md) | Step-by-step Facebook OAuth setup |

## API Endpoints Overview

```
POST   /token                          Login (username/password -> JWT tokens)
POST   /token/validate                 Validate token (internal service use)
POST   /refresh_token                  Refresh token pair (with replay detection)
GET    /.well-known/jwks.json          Public keys for token verification

GET    /auth/sessions                  List active sessions
DELETE /auth/sessions/{id}             Revoke a session
DELETE /auth/sessions                  Logout all other devices

POST   /users/                         Register new user
GET    /users/me/                      Get current user (authenticated)
GET    /users/{id}                     Get user by ID
PUT    /users/{id}                     Update user
DELETE /users/{id}                     Delete user
POST   /users/search                   Search by email or username

POST   /profile/                       Create profile
GET    /profile/me/                    Get own profile
PUT    /profile/me/                    Update profile
DELETE /profile/me/                    Delete profile
POST   /profile/me/picture             Upload avatar
DELETE /profile/me/picture             Delete avatar

GET    /auth/sso/providers             List configured SSO providers
GET    /auth/sso/{provider}/authorize  Start SSO login
GET    /auth/sso/{provider}/callback   SSO callback (returns tokens)
GET    /auth/sso/{provider}/link       Link SSO to existing account
DELETE /auth/sso/{provider}/unlink     Unlink SSO provider
GET    /auth/sso/linked                List linked providers

GET    /.well-known/openid-configuration   OIDC discovery
GET    /oauth/authorize                    Authorization code request
POST   /oauth/token                        Token exchange
GET    /oauth/userinfo                     User claims by scope

POST   /admin/clients                      Register OAuth client
GET    /admin/clients                      List clients
GET    /admin/clients/{id}                 Get client
PUT    /admin/clients/{id}                 Update client
POST   /admin/clients/{id}/rotate-secret   Rotate client secret
```
