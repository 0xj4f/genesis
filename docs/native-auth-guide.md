# Native Auth Guide - End-to-End Walkthrough

This guide walks through the complete native authentication flow using curl commands against a running Genesis instance.

**Base URL:** `http://localhost:8001` (Docker Compose default)

---

## 1. Register a User

```bash
curl -X POST http://localhost:8001/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jdoe",
    "email": "jdoe@example.com",
    "password": "MySecurePass123!"
  }'
```

**Password rules:**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character: `@#$%^&+=!`

**Response:**
```json
{
  "id": "c9220ae9-1dd0-4895-9acf-3a13dc4bcf31",
  "username": "jdoe",
  "email": "jdoe@example.com",
  "disabled": false,
  "is_active": true,
  "email_verified": false,
  "auth_provider": "native",
  "is_native": true,
  "last_login_at": null,
  "last_login_method": null,
  "created_at": "2026-04-16T05:49:19",
  "last_modified": "2026-04-16T05:49:19"
}
```

Notice `auth_provider: "native"` and `is_native: true` -- this user was registered with a password.

---

## 2. Login

```bash
curl -X POST http://localhost:8001/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jdoe&password=MySecurePass123!"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImdlbmVzaXMtZGV2LTEi....",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImdlbmVzaXMtZGV2LTEi....",
  "id_token": null
}
```

Save the access token for subsequent requests:

```bash
export TOKEN="eyJhbGciOiJSUzI1NiIs...."
```

---

## 3. Inspect the JWT

Your access token is an RS256-signed JWT. Decode it (without verification) to see the claims:

```bash
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

**Header** (`alg`, `kid`, `typ`):
```json
{
  "alg": "RS256",
  "kid": "genesis-dev-1",
  "typ": "JWT"
}
```

**Payload** (claims):
```json
{
  "iss": "http://localhost:8000",
  "aud": ["genesis-api"],
  "iat": 1776318560,
  "nbf": 1776318560,
  "exp": 1776320360,
  "jti": "8e91d291-1fd2-4f68-ab75-57445ecec4ae",
  "sub": "c9220ae9-1dd0-4895-9acf-3a13dc4bcf31",
  "username": "jdoe",
  "email": "jdoe@example.com",
  "email_verified": false,
  "auth_method": "password",
  "scope": "openid profile email",
  "sid": "64703535-8c75-499a-bc22-6a4ca30fb8ee"
}
```

Key claims:
- `sub` = user ID (UUID), not the username
- `sid` = session ID (ties this token to a server-side session)
- `scope` = granted scopes
- `auth_method` = how the user authenticated
- `kid` = which key signed this token (for JWKS lookup)

---

## 4. Access a Protected Endpoint

```bash
curl http://localhost:8001/users/me/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** Returns your full user object. The `last_login_at` and `last_login_method` fields are now populated.

---

## 5. Create a Profile

```bash
curl -X POST http://localhost:8001/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "given_name": "Jane",
    "family_name": "Doe",
    "nick_name": "jdoe",
    "sub": "jdoe",
    "locale": "en-US",
    "timezone": "America/New_York"
  }'
```

**Response:**
```json
{
  "user_id": "c9220ae9-...",
  "given_name": "Jane",
  "family_name": "Doe",
  "nick_name": "jdoe",
  "picture": null,
  "email": "jdoe@example.com",
  "sub": "jdoe",
  "locale": "en-US",
  "timezone": "America/New_York",
  "id": 1,
  "picture_key": null,
  "picture_updated_at": null,
  "updated_at": "2026-04-16T05:50:00"
}
```

---

## 6. Upload a Profile Picture

```bash
curl -X POST http://localhost:8001/profile/me/picture \
  -H "Authorization: Bearer $TOKEN" \
  -F "picture=@/path/to/photo.jpg"
```

**Response:**
```json
{
  "picture": "http://localhost:8000/avatars/c9220ae9-.../a1b2c3d4.webp",
  "picture_key": "avatars/c9220ae9-.../a1b2c3d4.webp"
}
```

The image is automatically:
- Validated (JPEG, PNG, WebP, or GIF; max 5 MB; magic byte check)
- Resized to 400x400 max
- Converted to WebP format
- Stored with a UUID filename tied to your user ID

---

## 7. View Your Profile

```bash
curl http://localhost:8001/profile/me/ \
  -H "Authorization: Bearer $TOKEN"
```

The `picture` field now contains the avatar URL.

---

## 8. List Active Sessions

```bash
curl http://localhost:8001/auth/sessions \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "64703535-8c75-499a-bc22-6a4ca30fb8ee",
      "ip_address": "172.66.0.243",
      "device_name": "Chrome on macOS",
      "login_method": "password",
      "created_at": "2026-04-16T05:49:20",
      "last_activity_at": "2026-04-16T05:49:20",
      "is_current": true
    }
  ],
  "total": 1
}
```

Each login creates a session. The `is_current` flag tells you which session belongs to this token.

---

## 9. Refresh Your Token

When your access token expires (default: 30 minutes), use the refresh token to get a new pair:

```bash
curl -X POST http://localhost:8001/refresh_token \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

**Response:** A new `access_token` + `refresh_token`. The old refresh token is invalidated.

**Replay detection:** If someone tries to reuse your old refresh token, the entire session is revoked for security. Both parties must re-authenticate.

---

## 10. Revoke a Specific Session

If you see a session you don't recognize (e.g., from another device):

```bash
curl -X DELETE http://localhost:8001/auth/sessions/64703535-8c75-499a-bc22-6a4ca30fb8ee \
  -H "Authorization: Bearer $TOKEN"
```

That session's refresh token is immediately invalidated.

---

## 11. Logout From All Devices

Revoke every session except your current one:

```bash
curl -X DELETE http://localhost:8001/auth/sessions \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "message": "Revoked 3 session(s)"
}
```

---

## What Happens Under the Hood

```
Register (/users/)
  -> bcrypt hash password
  -> insert user row (auth_provider=native, is_native=true)

Login (/token)
  -> verify password with bcrypt
  -> generate refresh JTI (UUID)
  -> create session row (bound to refresh JTI)
  -> sign access token (RS256, kid in header, sub=user_id, sid=session_id)
  -> sign refresh token (RS256, token_type=refresh, same sid)
  -> update user.last_login_at

Refresh (/refresh_token)
  -> decode refresh token, extract jti + sid
  -> look up session, verify jti matches session.refresh_token_jti
  -> if mismatch: REVOKE session (replay attack detected)
  -> if match: generate new tokens, update session.refresh_token_jti

Protected endpoint
  -> extract Bearer token
  -> decode header, get kid
  -> look up public key from JWKS cache
  -> verify signature, iss, aud, exp, nbf
  -> reject if token_type=refresh (can't use refresh as access)
  -> load user from DB by sub (user_id)
  -> check user.disabled and user.is_active
```
