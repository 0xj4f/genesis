# GitHub SSO Setup

This guide walks through creating a GitHub OAuth App so users can log into Genesis with their GitHub account.

---

## Step 1: Create an OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
   - Or: GitHub > **Settings** (your profile) > **Developer settings** > **OAuth Apps**
2. Click **New OAuth App**
3. Fill in the form:
   - **Application name:** `Genesis IAM` (or your project name)
   - **Homepage URL:** `http://localhost:8001` (or your production URL)
   - **Application description:** (optional)
   - **Authorization callback URL:**
     ```
     http://localhost:8000/auth/sso/github/callback
     ```
     For production:
     ```
     https://auth.yourdomain.com/auth/sso/github/callback
     ```
4. Click **Register application**

## Step 2: Copy Credentials

After creating the app, you'll see the app settings page:

1. **Client ID** is displayed at the top (e.g., `Iv1.abc123def456`)
2. Click **Generate a new client secret**
3. Copy the **Client Secret** immediately (it won't be shown again)

## Step 3: Configure Genesis

Add to your `docker-compose.yml` environment section (or `.env` file):

```yaml
GITHUB_CLIENT_ID: "Iv1.abc123def456"
GITHUB_CLIENT_SECRET: "your_client_secret_here"
```

Restart the API:
```bash
docker compose up -d api
```

## Step 4: Test

1. Verify GitHub is listed:
   ```bash
   curl http://localhost:8001/auth/sso/providers
   # Should include "github"
   ```

2. Open in your browser:
   ```
   http://localhost:8001/auth/sso/github/authorize
   ```

3. You'll see GitHub's authorization page asking to grant access
4. After authorizing, GitHub redirects back to Genesis
5. Genesis returns JWT tokens

---

## Notes

- **No review required:** Unlike Google, GitHub OAuth Apps work immediately for all GitHub users. No app review process.
- **Email access:** Genesis requests the `read:user user:email` scopes. If the user's email is private on GitHub, Genesis fetches it from the `/user/emails` API endpoint (only verified primary emails are used).
- **Callback URL must match exactly:** The callback URL in GitHub must match `{OAUTH_ISSUER}/auth/sso/github/callback`.
- **Organization restrictions:** If a user belongs to a GitHub organization that restricts OAuth app access, they may need to request approval from an org admin.

## What Genesis Receives from GitHub

```json
{
  "id": 12345678,
  "login": "jdoe",
  "name": "Jane Doe",
  "email": "jdoe@example.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4"
}
```

- `id` is used as `provider_user_id` (stable, never changes)
- `login` is used as the basis for the Genesis username (with collision handling)
- `avatar_url` is set as the profile picture
- `email` comes from `/user/emails` if not in the user response (only verified emails)
