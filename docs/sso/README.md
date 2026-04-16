# SSO - Social Sign-On

Genesis supports login via **Google**, **GitHub**, and **Facebook** using the OAuth2 Authorization Code flow. Users can sign up with a provider (no password needed), or link providers to an existing password-based account.

---

## How It Works

```
User        Genesis                     Provider (Google/GitHub/Facebook)
  |            |                            |
  |-- GET /auth/sso/google/authorize ------>|
  |            |-- 302 redirect ----------->|  (user sees Google login page)
  |            |                            |
  |            |<-- redirect with code -----|  (user authorized)
  |            |   /auth/sso/google/callback?code=...&state=...
  |            |                            |
  |            |-- exchange code for tokens->|
  |            |<-- access_token, userinfo --|
  |            |                            |
  |<-- Genesis JWT tokens -----------------|
```

1. User visits `/auth/sso/{provider}/authorize`
2. Genesis redirects to the provider's login page (with CSRF `state` parameter)
3. User authenticates with the provider
4. Provider redirects back to Genesis with an authorization `code`
5. Genesis exchanges the code for the provider's access token
6. Genesis fetches the user's profile from the provider
7. Genesis issues its own JWT tokens (access + refresh)

---

## Three Scenarios on Callback

When Genesis receives the callback, it handles three cases:

### 1. Returning SSO User
The provider account is already linked in `oauth_accounts`. Genesis loads the linked user and issues tokens.

### 2. New SSO User, Email Matches Existing Account
No `oauth_accounts` row exists, but a user with the same email is found:
- If the existing account has **verified email**: auto-link the SSO provider and issue tokens
- If **not verified**: return an error asking the user to log in with their password and verify email first

### 3. Entirely New User
No matching account at all. Genesis:
- Creates a new user (no password, `is_native=false`, `auth_provider=google/github/facebook`)
- Creates a profile from the provider's data (name, picture)
- Links the provider account
- Issues tokens

---

## Account Linking

An authenticated user can link additional SSO providers to their account:

```bash
# Link Google (opens browser redirect)
GET /auth/sso/google/link
Authorization: Bearer <token>

# List linked providers
GET /auth/sso/linked
Authorization: Bearer <token>

# Unlink Google
DELETE /auth/sso/google/unlink
Authorization: Bearer <token>
```

**Safety:** You cannot unlink the only authentication method. If the user has no password and only one SSO provider linked, the unlink is rejected.

---

## Configuration

Set these environment variables in `docker-compose.yml` or `.env`:

| Provider | Variables |
|----------|-----------|
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| GitHub | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |
| Facebook | `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET` |

**Callback URLs** are auto-generated as `{OAUTH_ISSUER}/auth/sso/{provider}/callback`. Override with `GOOGLE_REDIRECT_URI`, `GITHUB_REDIRECT_URI`, `FACEBOOK_REDIRECT_URI` if needed.

---

## Check Which Providers Are Configured

```bash
curl http://localhost:8001/auth/sso/providers
```

Returns only providers that have both `CLIENT_ID` and `CLIENT_SECRET` set:
```json
{
  "providers": ["google", "github"]
}
```

---

## Provider Setup Guides

- [Google SSO Setup](google.md) - Google Cloud Console credentials
- [GitHub SSO Setup](github.md) - GitHub OAuth App registration
- [Facebook SSO Setup](facebook.md) - Meta Developer App configuration
