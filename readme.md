# Genesis IAM

> The first identity. The origin of access.

Genesis is an open-source Identity & Access Management microservice built for developers who need a single, self-hosted auth backend across all their projects. Instead of re-implementing login, registration, JWT validation, session management, and SSO integration in every new app you build, Genesis handles it once -- and every project you create connects to it.

Built by [0xj4f](https://github.com/0xj4f).

---

## The Problem

Every time you start a new project -- ecommerce, payment gateway, internal tool, SaaS -- you rebuild the same auth layer:

- User registration and login
- Password hashing and validation
- JWT token generation and refresh
- Session management
- Social login (Google, GitHub, Facebook)
- Profile management
- Admin user management

Each implementation diverges. Tokens aren't interoperable. User databases are siloed. Session management is an afterthought. And when you need to add SSO or OIDC six months later, you're retrofitting it into code that wasn't designed for it.

## What Genesis Solves

Genesis is your **universal auth microservice**. Deploy it once, connect every project to it.

- **One user database** across all your apps. A user registers once and authenticates everywhere.
- **One login page** with native credentials and social SSO (Google, GitHub, Facebook).
- **One token format** -- RS256 JWTs with JWKS so any downstream service can verify tokens locally without calling Genesis on every request.
- **One session manager** with device tracking, concurrent session limits, and revocation.
- **One admin dashboard** to manage users, roles, and OAuth clients across your entire ecosystem.
- **Standard OIDC provider** -- your apps integrate with Genesis using any off-the-shelf OpenID Connect library.

### For Your Ecommerce App
Point your ecommerce frontend at Genesis for login. Users get JWTs with `aud: ["ecommerce-api"]`. Your ecommerce API validates tokens against Genesis's JWKS endpoint. No auth code in your ecommerce repo.

### For Your Payment Gateway
Register a `payment-gateway` OAuth client in Genesis. Your payment service authenticates via client credentials (machine-to-machine). User-facing flows use the same Genesis login.

### For Your Internal Tools
Your admin panels and internal dashboards redirect to Genesis via OIDC. Single sign-on across every tool you build, with role-based access control baked in.

---

## Features

| Feature | Description |
|---------|-------------|
| **Native Auth** | Username/password registration with bcrypt, password policy enforcement |
| **SSO Login** | Google, GitHub, Facebook via OAuth2 Authorization Code flow |
| **RS256 JWT** | Asymmetric token signing with key rotation and JWKS endpoint |
| **OIDC Provider** | Full OpenID Connect provider -- any OIDC client library works |
| **Session Management** | Server-side sessions, device tracking, concurrent limits, replay detection |
| **Profile + Avatar** | User profiles with picture upload (local or S3 storage) |
| **Admin Dashboard** | User analytics, paginated user list, role management, detail pane |
| **RBAC** | Role-based access control (user / admin / root) enforced at JWT level |
| **Multi-Project** | OAuth client registration with audience and scope isolation |
| **Client Credentials** | Machine-to-machine authentication for backend services |
| **PKCE** | Proof Key for Code Exchange for public clients (SPAs, mobile) |
| **Account Linking** | Link/unlink multiple SSO providers to a single account |
| **Docker Ready** | One `docker compose up` for the full stack |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python) |
| Database | MySQL 8.0 + SQLAlchemy + Alembic |
| Auth | RS256 JWT (python-jose), bcrypt, OAuth2, OIDC |
| Frontend | Vue 3 + Vuex + Vue Router |
| Containerization | Docker + Docker Compose + Nginx |

---

## Quickstart

```bash
git clone https://github.com/0xj4f/genesis.git
cd genesis
docker compose up -d
```

Three services start:
- **API** on `http://localhost:8001` (FastAPI + Swagger at `/docs`)
- **Web** on `http://localhost:8082` (Vue frontend)
- **MySQL** on port `3306`

On first boot, Genesis:
1. Generates RSA signing keys
2. Runs database migrations (creates 8 tables)
3. Seeds **Adam** -- the ROOT superadmin (credentials printed in API logs)

```bash
# View Adam's credentials
docker compose logs api | grep -A 5 "ROOT USER"
```

### Try It

```bash
# Register a user
curl -X POST http://localhost:8001/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "email": "demo@test.com", "password": "SecurePass123!"}'

# Login
curl -X POST http://localhost:8001/token \
  -d "username=demo&password=SecurePass123!"

# Admin login (browser)
open http://localhost:8082/admin/login
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Docker setup, environment variables, local development |
| [Native Auth Guide](docs/native-auth-guide.md) | End-to-end walkthrough: register, login, profile, sessions |
| [API Reference](docs/api-reference.md) | All 40+ endpoints with curl examples |
| [OIDC Integration](docs/oidc-guide.md) | How downstream apps authenticate via Genesis |
| [SSO Setup](docs/sso/README.md) | Overview of Social Sign-On |
| [Google SSO](docs/sso/google.md) | Step-by-step Google OAuth credentials |
| [GitHub SSO](docs/sso/github.md) | Step-by-step GitHub OAuth App setup |
| [Facebook SSO](docs/sso/facebook.md) | Step-by-step Meta App configuration |

---

## Architecture

```
Browser / App / Service
        |
        v
  +------------------+
  |   Vue 3 Frontend | :8082  (Nginx)
  +------------------+
        |
        v
  +------------------+
  |  FastAPI Backend  | :8001
  |                  |
  |  /token           - native login
  |  /auth/sso/*      - social login
  |  /oauth/*         - OIDC provider
  |  /admin/*         - admin dashboard API
  |  /users/*         - user CRUD
  |  /profile/*       - profile + avatar
  |  /auth/sessions   - session mgmt
  |  /.well-known/*   - JWKS + OIDC discovery
  +------------------+
        |
        v
  +------------------+
  |    MySQL 8.0     | :3306
  |                  |
  |  users, profiles, sessions,
  |  oauth_accounts, oauth_clients,
  |  authorization_codes, jwk_keys
  +------------------+
```

## API Overview

```
POST   /token                          Native login
POST   /admin/login                    Admin login (role >= admin)
POST   /refresh_token                  Token refresh with replay detection
POST   /token/validate                 Internal token validation
GET    /.well-known/jwks.json          Public keys (JWKS)
GET    /.well-known/openid-configuration   OIDC discovery

POST   /users/                         Register
GET    /users/me/                      Current user

POST   /profile/                       Create profile
GET    /profile/me/                    Get profile
POST   /profile/me/picture             Upload avatar

GET    /auth/sessions                  List sessions
DELETE /auth/sessions/{id}             Revoke session
DELETE /auth/sessions                  Logout all devices

GET    /auth/sso/providers             Configured SSO providers
GET    /auth/sso/{provider}/authorize  Start SSO login
GET    /auth/sso/{provider}/callback   SSO callback

GET    /oauth/authorize                OIDC authorization
POST   /oauth/token                    OIDC token exchange
GET    /oauth/userinfo                 OIDC user claims

GET    /admin/analytics                User analytics
GET    /admin/users?page=1&search=     Paginated user list
GET    /admin/users/{id}               User detail
POST   /admin/users/{id}/role          Change role
POST   /admin/users/{id}/disable       Toggle disable
POST   /admin/clients                  Register OAuth client
```

---

## License

MIT

---

<p align="center">
  <sub>built by <a href="https://github.com/0xj4f">0xj4f</a></sub>
</p>
