# OIDC Integration Guide

Genesis acts as an **OpenID Connect Provider (OP)**. Your downstream applications (ecommerce, internal tools, etc.) can authenticate users through Genesis using standard OIDC libraries.

---

## Integration Patterns

Genesis supports three ways for downstream apps to verify identity:

### Pattern 1: Direct Token Validation (Simplest)

Your app sends the user's access token to Genesis for validation.

```
Your App                         Genesis
  |                                |
  |-- POST /token/validate ------->|
  |   (Bearer: user's token)       |
  |<-- { user_id, username } ------|
```

```bash
curl -X POST http://localhost:8001/token/validate \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Pros:** Simple. **Cons:** Every request hits Genesis.

### Pattern 2: JWKS Local Validation (Recommended for APIs)

Your app fetches Genesis's public keys once and validates tokens locally.

```
Your App                         Genesis
  |                                |
  |-- GET /.well-known/jwks.json ->|  (once, cached)
  |<-- { keys: [...] } -----------|
  |                                |
  |  (validate JWT locally         |
  |   using cached public key)     |
```

Use any JWT library that supports JWKS:
- **Python:** `python-jose`, `PyJWT`
- **Node.js:** `jose`, `jsonwebtoken`
- **Go:** `go-jose`

```python
# Python example
from jose import jwt, jwk
import requests

# Fetch JWKS (cache this!)
jwks = requests.get("http://localhost:8001/.well-known/jwks.json").json()

# Decode and verify token
decoded = jwt.decode(
    token,
    jwks,
    algorithms=["RS256"],
    audience="genesis-api",
    issuer="http://localhost:8000",
)
user_id = decoded["sub"]
```

**Pros:** Fast, no network call per request. **Cons:** Slight setup.

### Pattern 3: Full OIDC Flow (Standard for Web Apps)

Your app redirects users to Genesis for login, then receives tokens via callback. This is the standard OIDC Authorization Code flow.

```
User        Your App              Genesis
  |            |                     |
  |-- visit -->|                     |
  |            |-- redirect -------->| GET /oauth/authorize
  |            |                     |   (user logs in)
  |<-----------|-- redirect ---------|   ?code=...&state=...
  |            |                     |
  |            |-- POST /oauth/token |   (exchange code)
  |            |<-- tokens ----------|   { access_token, id_token }
```

---

## Full OIDC Flow Walkthrough

### Step 1: Register an OAuth Client

Via CLI:
```bash
docker compose exec api python -m app.cli create-client my-web-app \
  --redirect-uris "http://localhost:3000/callback" \
  --scopes "openid,profile,email,offline_access" \
  --audiences "genesis-api" \
  --grant-types "authorization_code,refresh_token"
```

Or via API:
```bash
curl -X POST http://localhost:8001/admin/clients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "client_name": "my-web-app",
    "redirect_uris": ["http://localhost:3000/callback"],
    "allowed_scopes": ["openid", "profile", "email", "offline_access"],
    "allowed_audiences": ["genesis-api"],
    "grant_types": ["authorization_code", "refresh_token"]
  }'
```

Save the `client_id` and `client_secret` from the response.

### Step 2: Redirect User to Authorize

Build the authorization URL and redirect the user:

```
http://localhost:8001/oauth/authorize
  ?response_type=code
  &client_id=<client_id>
  &redirect_uri=http://localhost:3000/callback
  &scope=openid profile email offline_access
  &state=<random_string>
  &nonce=<random_string>
```

The user must be authenticated (send their Genesis access token as Bearer). Genesis auto-approves consent for first-party clients and redirects back with an authorization code.

### Step 3: Exchange Code for Tokens

```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code=<authorization_code>" \
  -d "redirect_uri=http://localhost:3000/callback" \
  -d "client_id=<client_id>" \
  -d "client_secret=<client_secret>"
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "scope": "openid profile email offline_access",
  "refresh_token": "eyJ...",
  "id_token": "eyJ..."
}
```

### Step 4: Use the ID Token

The `id_token` is a JWT containing the user's identity claims:

```json
{
  "iss": "http://localhost:8000",
  "sub": "c9220ae9-1dd0-4895-...",
  "aud": "<client_id>",
  "iat": 1776320228,
  "exp": 1776322028,
  "auth_time": 1776320228,
  "at_hash": "aOtwcVm3CsVK...",
  "nonce": "<your_nonce>",
  "email": "jdoe@example.com",
  "email_verified": false,
  "name": "Jane Doe",
  "given_name": "Jane",
  "family_name": "Doe"
}
```

Verify the `nonce` matches what you sent in Step 2.

### Step 5: Get User Info

```bash
curl http://localhost:8001/oauth/userinfo \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Returns claims based on granted scopes:
- `openid` -> `sub`
- `email` -> `email`, `email_verified`
- `profile` -> `name`, `given_name`, `family_name`, `nickname`, `picture`, `locale`

---

## PKCE (for Public Clients / SPAs)

Public clients (no server-side secret) must use PKCE:

```bash
# Generate code verifier (43-128 chars)
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=/+' | head -c 43)

# Generate code challenge (S256)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '=')

# Authorize with PKCE
GET /oauth/authorize
  ?response_type=code
  &client_id=<client_id>
  &redirect_uri=...
  &scope=openid profile email
  &state=...
  &code_challenge=$CODE_CHALLENGE
  &code_challenge_method=S256

# Exchange code with verifier
POST /oauth/token
  grant_type=authorization_code
  &code=...
  &redirect_uri=...
  &client_id=<client_id>
  &code_verifier=$CODE_VERIFIER
```

---

## Client Credentials (Machine-to-Machine)

For service-to-service authentication without a user context:

```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=<client_id>" \
  -d "client_secret=<client_secret>" \
  -d "scope=openid"
```

Returns an access token where `sub` = client_id (no user). No refresh token or ID token.

---

## Supported Scopes

| Scope | Claims | Description |
|-------|--------|-------------|
| `openid` | `sub` | Required for OIDC. Triggers ID token issuance |
| `profile` | `name`, `given_name`, `family_name`, `nickname`, `picture`, `locale` | User profile data |
| `email` | `email`, `email_verified` | Email address |
| `offline_access` | (none) | Enables refresh token issuance |

Custom scopes (configured per client): `ecommerce:read`, `ecommerce:write`, `payments:read`, `admin`, etc.

---

## Discovery Document

```bash
curl http://localhost:8001/.well-known/openid-configuration
```

Standard OIDC libraries use this to auto-configure endpoints, supported algorithms, and available scopes.
