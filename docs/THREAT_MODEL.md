# STRIDE Threat Model

Repository: `0xj4f/genesis`  
Date: February 18, 2026  
Assessor: Codex

## Scope
This document covers the security threat model for the FastAPI backend and Vue frontend in this repository.

In scope:
- Backend API routes and auth flows in `app/`
- Data models and persistence interfaces in `app/models` and `app/database`
- Frontend token handling and API calls in `web/src`

Out of scope:
- Cloud/network infrastructure controls (not present in repo)
- CI/CD platform configuration (not present in repo)

## Method
STRIf you want, I can draft this as MVP_PRODUCT_PLAN.md with user stories + acceptance criteria.

IDE was applied to:
- Entry points (HTTP endpoints)
- Trust boundaries
- Data flows for credentials, tokens, and profile/user data
- Storage and logging behavior

## System Overview
### Main Components
- FastAPI app bootstrap and middleware: `app/main.py`
- Auth/token logic: `app/auth/auth.py`, `app/services/auth_service.py`, `app/routes/auth.py`
- User API: `app/routes/users.py`, `app/services/user_service.py`, `app/database/user_db_interface.py`
- Profile API: `app/routes/profiles.py`, `app/services/profile_service.py`, `app/database/profile_db_interface.py`
- Database session and connection: `app/database/session.py`
- Frontend SPA and token usage: `web/src/components/LoginForm.vue`, `web/src/store/index.js`

### Trust Boundaries
1. Browser/client -> Backend API
2. Backend API -> MySQL database
3. Frontend runtime state (in-browser) -> protected API operations

### Key Assets
- User credentials and password hashes
- Access and refresh JWTs
- User/profile personally identifiable information (PII)
- Account status (`disabled`)

## Data Flow Summary
1. User registers via `POST /users/`.
2. User authenticates via `POST /token` and receives access/refresh tokens.
3. Bearer access token is used for protected profile routes (`/profile/me/`).
4. Refresh token is presented to `POST /refresh_token` to mint new tokens.
5. User and profile records are persisted in MySQL.

## STRIDE Analysis

### S: Spoofing
Threats:
- JWT spoofing risk if environment secret is not set and fallback secret is used (`app/auth/auth.py:17`).
- Internal validation route is publicly reachable (`app/routes/auth.py:23`).

Impact:
- Attacker can impersonate users by forging or replaying tokens under weak key management.

Existing controls:
- JWT signature verification with issuer/audience checks (`app/auth/auth.py:54`).

Gaps:
- Insecure default for signing key.
- No endpoint-level restriction for internal-only token validation path.

### T: Tampering
Threats:
- Unauthenticated modification/deletion of users (`app/routes/users.py:37`, `app/routes/users.py:44`).
- Client can set `disabled` in create model (`app/models/user_api_model.py:12`).

Impact:
- Unauthorized account changes, destructive data tampering.

Existing controls:
- Pydantic validation and SQLAlchemy ORM usage.

Gaps:
- Missing authorization checks on critical user-management routes.
- Overly permissive API model surface.

### R: Repudiation
Threats:
- Security-sensitive events are not audit logged with actor/context.
- Debug `print` statements emit token/user details without structured traceability (`app/auth/auth.py:75`, `app/auth/auth.py:83`, `app/auth/auth.py:90`, `app/auth/auth.py:108`).

Impact:
- Weak forensic capability and unclear accountability.

Existing controls:
- Basic app logger initialization (`app/main.py:26`).

Gaps:
- No audit trail for auth events, profile changes, user mutations.

### I: Information Disclosure
Threats:
- Unauthenticated user listing/search/read endpoints expose user data (`app/routes/users.py:26`, `app/routes/users.py:30`, `app/routes/users.py:51`).
- Tokens/payloads are printed in server output (`app/auth/auth.py:75`, `app/auth/auth.py:108`).
- CORS policy allows all origins with credentials enabled (`app/main.py:14`, `app/main.py:19`).

Impact:
- PII leakage, token leakage, expanded attack surface for browser-based abuse.

Existing controls:
- Password hashing with bcrypt (`app/utils/security.py`).

Gaps:
- Sensitive operational data in logs.
- Overly broad cross-origin policy.
- Excessive data exposure from user endpoints.

### D: Denial of Service
Threats:
- No apparent rate limiting or brute-force protections for login (`app/routes/auth.py:15`).
- User enumeration/list endpoints may be abused for repeated load (`app/routes/users.py:26`).

Impact:
- Resource exhaustion, degraded availability, credential-stuffing amplification.

Existing controls:
- None visible in repo.

Gaps:
- No API throttling, no account lockout/backoff, no abuse controls.

### E: Elevation of Privilege
Threats:
- Missing role-based access control on user management routes (`app/routes/users.py`).
- Refresh endpoint accepts any valid JWT payload without token-type distinction (`app/services/auth_service.py:37`).

Impact:
- Unauthorized privilege gain and session lifetime extension.

Existing controls:
- Token validation enforces `exp/iat/nbf/aud/iss` (`app/auth/auth.py:54`).

Gaps:
- No role model/policy enforcement.
- No strict refresh-token semantics.

## Risk Register

| ID | STRIDE | Risk | Evidence | Severity | Likelihood | Priority |
|---|---|---|---|---|---|---|
| R1 | E/T/I | Unauthenticated user management endpoints allow read/update/delete and enumeration | `app/routes/users.py:26`, `app/routes/users.py:30`, `app/routes/users.py:37`, `app/routes/users.py:44`, `app/routes/users.py:51` | Critical | High | P0 |
| R2 | S/E | Hardcoded JWT secret fallback enables token forgery when env is missing/misconfigured | `app/auth/auth.py:17` | Critical | Medium | P0 |
| R3 | E | Refresh token flow does not enforce token type; any valid token can be reused for refresh | `app/services/auth_service.py:37`, `app/auth/auth.py:30` | High | High | P0 |
| R4 | I/R | Sensitive token and payload data logged via `print` | `app/auth/auth.py:75`, `app/auth/auth.py:83`, `app/auth/auth.py:108` | High | Medium | P1 |
| R5 | I | CORS configured as wildcard origin with credentials allowed | `app/main.py:14`, `app/main.py:19` | High | Medium | P1 |
| R6 | D | No login brute-force/rate limit controls | `app/routes/auth.py:15` | Medium | High | P1 |
| R7 | T/E | Client-writable `disabled` field in user create model | `app/models/user_api_model.py:12`, `app/routes/users.py:19` | Medium | Medium | P2 |

## Recommended Mitigation Plan

### P0 (Immediate)
1. Protect all user management routes.
- Require authentication for `/users/*` except registration if intended public.
- Add authorization policy (admin-only for list/search/update/delete, or strict self-service ownership checks).

2. Enforce secure JWT key management.
- Remove fallback default in `app/auth/auth.py`.
- Fail fast on startup if `OAUTH_SECRET_KEY` is unset or weak.
- Rotate any previously used default/fallback key.

3. Separate access vs refresh token semantics.
- Add `token_type` claim (`access`/`refresh`).
- Enforce `token_type == refresh` in `/refresh_token` service.
- Consider refresh token rotation and server-side revocation list keyed by `jti`.

### P1 (Near-term)
4. Replace debug prints with structured logging.
- Remove raw token/payload output.
- Add audit logs for auth success/failure, refresh, user/profile mutations, including actor ID and request ID.

5. Tighten CORS.
- Replace `origins = ["*"]` with explicit allowed origins by environment.
- Avoid `allow_credentials=True` with broad origins.

6. Add abuse protection.
- Add rate limits for `/token`, `/refresh_token`, and high-volume read endpoints.
- Add failed-login backoff/lockout and alerting.

### P2 (Hardening)
7. Reduce API model attack surface.
- Make `disabled` server-controlled only.
- Split response schema from create/update schema to avoid accidental sensitive field exposurethreat_model.

8. Expand security test coverage.
- Add negative tests proving unauthorized requests to user-management routes are rejected.
- Add tests for refresh token type enforcement and token replay behavior.

## Validation Checklist
- [ ] Unauthenticated caller cannot list/search/read arbitrary users.
- [ ] Non-admin caller cannot update/delete other users.
- [ ] App fails startup when `OAUTH_SECRET_KEY` is missing.
- [ ] Refresh endpoint rejects access tokens.
- [ ] No raw tokens appear in logs.
- [ ] CORS only allows approved frontend origins.
- [ ] Login endpoint enforces rate limits.

## Notes and Assumptions
- This model is repository-based and does not include deployment-layer controls.
- Severity reflects likely real-world impact for a typical internet-exposed identity/profile API.
- Findings should be re-scored after architecture changes (roles, gateway, WAF, SSO, key management).
