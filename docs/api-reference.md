# API Reference

**Base URL:** `http://localhost:8001` (Docker Compose)

**Authentication:** Endpoints marked with "Auth: Yes" require a Bearer token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

---

## Auth

### POST /token
Login with username and password.

- **Auth:** No
- **Content-Type:** `application/x-www-form-urlencoded`
- **Body:** `username=<string>&password=<string>`
- **Response:** `{ access_token, refresh_token, token_type, id_token }`

```bash
curl -X POST http://localhost:8001/token \
  -d "username=jdoe&password=SecurePass123!"
```

### POST /token/validate
Validate an access token and return the user identity. Designed for internal service-to-service calls.

- **Auth:** Yes
- **Response:** `{ user_id, username }`

```bash
curl -X POST http://localhost:8001/token/validate \
  -H "Authorization: Bearer $TOKEN"
```

### POST /refresh_token
Exchange a refresh token for a new access/refresh token pair. Implements rotation with replay detection.

- **Auth:** Bearer (refresh token)
- **Response:** `{ access_token, refresh_token, token_type }`

```bash
curl -X POST http://localhost:8001/refresh_token \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

### GET /.well-known/jwks.json
Public keys for verifying JWT signatures. Downstream services fetch this to validate tokens locally.

- **Auth:** No
- **Response:** `{ keys: [{ kty, use, alg, kid, n, e }] }`

```bash
curl http://localhost:8001/.well-known/jwks.json
```

---

## Sessions

### GET /auth/sessions
List all active sessions for the current user.

- **Auth:** Yes
- **Response:** `{ sessions: [{ id, ip_address, device_name, login_method, created_at, last_activity_at, is_current }], total }`

```bash
curl http://localhost:8001/auth/sessions \
  -H "Authorization: Bearer $TOKEN"
```

### DELETE /auth/sessions/{session_id}
Revoke a specific session. Invalidates its refresh token.

- **Auth:** Yes
- **Response:** `{ message }`

```bash
curl -X DELETE http://localhost:8001/auth/sessions/<session_id> \
  -H "Authorization: Bearer $TOKEN"
```

### DELETE /auth/sessions
Revoke all sessions except the current one (logout all other devices).

- **Auth:** Yes
- **Response:** `{ message }`

```bash
curl -X DELETE http://localhost:8001/auth/sessions \
  -H "Authorization: Bearer $TOKEN"
```

---

## Users

### POST /users/
Register a new user. Password must be 12+ characters with uppercase, lowercase, digit, and special character.

- **Auth:** No
- **Body:** `{ username, email, password }`
- **Response:** `{ id, username, email, disabled, is_active, email_verified, auth_provider, is_native, created_at, last_modified }`

```bash
curl -X POST http://localhost:8001/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "jdoe", "email": "jdoe@example.com", "password": "SecurePass123!"}'
```

### GET /users/
List all users.

- **Auth:** No
- **Response:** Array of User objects

### GET /users/{user_id}
Get a user by UUID.

- **Auth:** No
- **Response:** User object

### PUT /users/{user_id}
Update a user's username, email, or password.

- **Auth:** No
- **Body:** `{ username?, email?, password? }`
- **Response:** Updated User object

### DELETE /users/{user_id}
Delete a user.

- **Auth:** No
- **Response:** `{ message }`

### POST /users/search
Search for a user by email or username.

- **Auth:** No
- **Body:** `{ email? }` or `{ username? }`
- **Response:** User object (404 if not found)

```bash
curl -X POST http://localhost:8001/users/search \
  -H "Content-Type: application/json" \
  -d '{"email": "jdoe@example.com"}'
```

### GET /users/me/
Get the currently authenticated user.

- **Auth:** Yes
- **Response:** User object

```bash
curl http://localhost:8001/users/me/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## Profile

### POST /profile/
Create a profile for the authenticated user. The `user_id` and `email` are auto-set from the token.

- **Auth:** Yes
- **Body:** `{ given_name, family_name, nick_name?, picture?, sub, locale?, timezone? }`
- **Response:** Profile object

```bash
curl -X POST http://localhost:8001/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"given_name": "Jane", "family_name": "Doe", "sub": "jdoe"}'
```

### GET /profile/me/
Get the authenticated user's profile.

- **Auth:** Yes
- **Response:** `{ id, user_id, given_name, family_name, nick_name, picture, picture_key, email, sub, locale, timezone, updated_at }`

### PUT /profile/me/
Update profile fields.

- **Auth:** Yes
- **Body:** `{ given_name?, family_name?, nick_name?, picture?, locale?, timezone? }`
- **Response:** Updated Profile object

### DELETE /profile/me/
Delete the authenticated user's profile.

- **Auth:** Yes
- **Response:** `{ message }`

### POST /profile/me/picture
Upload a profile picture. Accepts JPEG, PNG, WebP, or GIF (max 5 MB). Auto-resized to 400x400 and converted to WebP.

- **Auth:** Yes
- **Content-Type:** `multipart/form-data`
- **Body:** File field named `picture`
- **Response:** `{ picture, picture_key }`

```bash
curl -X POST http://localhost:8001/profile/me/picture \
  -H "Authorization: Bearer $TOKEN" \
  -F "picture=@photo.jpg"
```

### DELETE /profile/me/picture
Delete the profile picture.

- **Auth:** Yes
- **Response:** `{ message }`

---

## SSO

### GET /auth/sso/providers
List which SSO providers are configured (have credentials set).

- **Auth:** No
- **Response:** `{ providers: ["google", "github", "facebook"] }`

### GET /auth/sso/{provider}/authorize
Start SSO login. Redirects the user to the provider's authorization page.

- **Auth:** No
- **Provider:** `google`, `github`, or `facebook`
- **Response:** HTTP 302 redirect

Open in a browser:
```
http://localhost:8001/auth/sso/google/authorize
```

### GET /auth/sso/{provider}/callback
Handle the OAuth callback from the provider. Returns JWT tokens.

- **Auth:** No
- **Query:** `code`, `state` (set by the provider)
- **Response:** `{ access_token, refresh_token, token_type }`

This endpoint handles three scenarios:
1. **Returning SSO user** - finds existing linked account, issues tokens
2. **Email matches verified native account** - auto-links the SSO provider
3. **New user** - creates account (no password, `is_native=false`), profile, and issues tokens

### GET /auth/sso/{provider}/link
Link an SSO provider to the authenticated user's existing account.

- **Auth:** Yes
- **Response:** HTTP 302 redirect to provider

### DELETE /auth/sso/{provider}/unlink
Unlink an SSO provider. Fails if it's the user's only authentication method (no password set).

- **Auth:** Yes
- **Response:** `{ message }`

### GET /auth/sso/linked
List all SSO providers linked to the authenticated user.

- **Auth:** Yes
- **Response:** `{ linked_providers: [{ provider, provider_email, provider_username, linked_at }] }`

---

## OIDC

### GET /.well-known/openid-configuration
OpenID Connect discovery document.

- **Auth:** No
- **Response:** Standard OIDC discovery JSON (issuer, endpoints, supported scopes/claims/algorithms)

### GET /oauth/authorize
Authorization endpoint. Requires an authenticated user. Returns a redirect with an authorization code.

- **Auth:** Yes (Bearer token)
- **Query params:** `response_type=code`, `client_id`, `redirect_uri`, `scope`, `state`, `nonce?`, `code_challenge?`, `code_challenge_method?`
- **Response:** HTTP 302 redirect to `redirect_uri?code=...&state=...`

### POST /oauth/token
Token endpoint. Supports three grant types.

- **Auth:** Client credentials (Basic auth or form params)
- **Content-Type:** `application/x-www-form-urlencoded`

**grant_type=authorization_code:**
```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=authorization_code&code=<code>&redirect_uri=<uri>&client_id=<id>&client_secret=<secret>"
```

**grant_type=refresh_token:**
```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=refresh_token&refresh_token=<token>"
```

**grant_type=client_credentials:**
```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials&client_id=<id>&client_secret=<secret>&scope=openid"
```

### GET /oauth/userinfo
Returns user claims based on the token's scopes. Requires `openid` scope.

- **Auth:** Yes (Bearer token with `openid` scope)
- **Response:** `{ sub, email?, email_verified?, name?, given_name?, family_name?, nickname?, picture?, locale? }`

```bash
curl http://localhost:8001/oauth/userinfo \
  -H "Authorization: Bearer $TOKEN"
```

---

## Admin

### POST /admin/clients
Register a new OAuth client. Returns the client secret (shown once).

- **Auth:** Yes
- **Body:** `{ client_name, redirect_uris[], allowed_scopes[], allowed_audiences[], grant_types?, is_confidential? }`
- **Response:** `{ id, client_name, client_secret, redirect_uris, allowed_scopes, allowed_audiences, grant_types, is_active, is_confidential }`

```bash
curl -X POST http://localhost:8001/admin/clients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "client_name": "my-app",
    "redirect_uris": ["http://localhost:3000/callback"],
    "allowed_scopes": ["openid", "profile", "email"],
    "allowed_audiences": ["genesis-api"]
  }'
```

### GET /admin/clients
List all registered OAuth clients.

- **Auth:** Yes
- **Response:** Array of OAuthClient objects

### GET /admin/clients/{client_id}
Get a specific client's details.

- **Auth:** Yes
- **Response:** OAuthClient object

### PUT /admin/clients/{client_id}
Update a client's configuration.

- **Auth:** Yes
- **Body:** `{ client_name?, redirect_uris?, allowed_scopes?, allowed_audiences?, grant_types?, is_active? }`

### POST /admin/clients/{client_id}/rotate-secret
Generate a new client secret. The old secret is immediately invalidated.

- **Auth:** Yes
- **Response:** `{ client_id, client_name, client_secret, message }`
