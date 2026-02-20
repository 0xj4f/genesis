# MVP Product Plan: Generic IAM Manager

Date: February 18, 2026  
Owner: Product + Engineering

## 1) Product Goal
Ship a production-ready MVP IAM service that supports:
- Native app users (email/username + password)
- Google SSO users
- Facebook SSO users
- User profile self-service
- Root admin with full management access
- JWT-based auth with session tracking and revocation

## 2) Target Users
- End user: registers/logs in and manages their own account/profile.
- Root admin: has god access to IAM APIs and operational controls.
- Internal client app: consumes IAM APIs for authentication and profile.

## 3) MVP Scope (In)
- Native registration/login/refresh/logout.
- Google OAuth login callback flow.
- Facebook OAuth login callback flow.
- `GET /users/me`, `PUT /users/me`.
- `GET /profile/me`, `PUT /profile/me`.
- Root admin bootstrap on first startup/migration.
- Admin APIs for user listing, user status changes, session revocation.
- Session tracking table + refresh token rotation.
- Basic audit logs for security-sensitive actions.

## 4) MVP Non-Goals (Out)
- Multi-tenant org hierarchy.
- Fine-grained policy engine (ABAC/Rego).
- Enterprise federation (SAML/OIDC enterprise providers).
- Advanced admin UI analytics.

## 5) Product Requirements
1. One canonical user identity per person (`users`), with many login identities (`user_identities`).
2. Native credentials stored separately from SSO identity records.
3. JWT access tokens are short-lived.
4. Refresh tokens are stored hashed and rotated per refresh.
5. Sessions are revocable per device/session and globally.
6. Root admin is generated once and persisted in DB.
7. Role-based auth is enforced server-side for admin actions.

## 6) Roles and Access
- `root_admin`: full access to all IAM APIs.
- `admin`: optional future role, limited management.
- `user`: self-service only.

Authorization rules for MVP:
- `user` can only read/update own `user` and `profile`.
- `root_admin` can read/update/disable/delete any user, list sessions, revoke sessions.

## 7) API Surface (MVP)
Public:
- `POST /auth/register` (native)
- `POST /auth/login` (native)
- `POST /auth/oauth/google/callback`
- `POST /auth/oauth/facebook/callback`
- `POST /auth/refresh`

Authenticated user:
- `POST /auth/logout`
- `POST /auth/logout-all`
- `GET /users/me`
- `PUT /users/me`
- `GET /profile/me`
- `PUT /profile/me`

Root admin:
- `GET /admin/users`
- `GET /admin/users/{user_id}`
- `PATCH /admin/users/{user_id}` (disable/enable, role updates)
- `GET /admin/sessions`
- `POST /admin/sessions/{session_id}/revoke`
- `GET /admin/audit-logs`

## 8) Security Baseline (Ship Criteria)
- No default JWT secret fallback.
- CORS only allows explicit client origins.
- Password hashing with bcrypt/argon2 and complexity validation.
- Rate limiting on login/refresh endpoints.
- No raw token logging.
- Audit logs for login/logout/refresh/admin mutations.
- JWT includes `sub`, `role`, `sid`, `jti`, `exp`, `iat`, `nbf`.

## 9) Milestones
M1: Foundation (week 1)
- Create new schema and migrations (`users`, `user_identities`, `user_credentials`, `sessions`, `audit_logs`).
- Root admin bootstrap command and idempotent startup check.

M2: Native Auth + Sessions (week 2)
- Register/login/refresh/logout.
- Refresh token rotation + hashed storage.
- `me` endpoints for user/profile.

M3: SSO Integration (week 3)
- Google OAuth callback and account linking rules.
- Facebook OAuth callback and account linking rules.
- Session creation parity with native logins.

M4: Admin Controls + Hardening (week 4)
- Admin APIs + RBAC middleware.
- Audit log endpoints.
- Rate limits and security tests.

## 10) Acceptance Criteria
1. New native user can register, login, refresh, logout, and edit own profile.
2. Google/Facebook user can login and receive same JWT/session model.
3. Root admin can manage all users and revoke sessions.
4. Disabled user cannot login or refresh.
5. Refresh token replay fails after rotation.
6. Unauthorized access to admin endpoints returns 403/401.
7. Audit logs show actor, action, target, and timestamp.

## 11) Major Risks and Controls
- Risk: account takeover through unsafe SSO linking.
- Control: never auto-link by email without verified ownership flow.

- Risk: privilege escalation through weak authz checks.
- Control: central RBAC dependency and endpoint-level tests.

- Risk: token theft/replay.
- Control: short access TTL, refresh hashing, rotation, revoke support.

## 12) Immediate Engineering Next Steps
1. Freeze schema contract in `docs/schema.md`.
2. Implement migrations and new ORM models.
3. Refactor current routes into `/auth`, `/users/me`, `/profile/me`, `/admin/*`.
4. Add authz middleware and session service.
5. Write auth/security integration tests before enabling SSO in production.

