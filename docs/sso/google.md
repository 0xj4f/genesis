# Google SSO Setup

This guide walks through creating Google OAuth 2.0 credentials so users can log into Genesis with their Google account.

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top and select **New Project**
3. Name it (e.g., `genesis-iam`) and click **Create**
4. Make sure the new project is selected in the dropdown

## Step 2: Configure the OAuth Consent Screen

1. In the left sidebar, go to **APIs & Services** > **OAuth consent screen**
2. Select **External** (allows any Google account to log in) and click **Create**
3. Fill in the required fields:
   - **App name:** Your app name (e.g., `Genesis Auth`)
   - **User support email:** Your email
   - **Developer contact information:** Your email
4. Click **Save and Continue**
5. On the **Scopes** screen, click **Add or Remove Scopes** and add:
   - `openid`
   - `email`
   - `profile`
6. Click **Update**, then **Save and Continue**
7. On **Test users**, add your Google email for testing (only needed while in "Testing" mode)
8. Click **Save and Continue**, then **Back to Dashboard**

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **+ Create Credentials** > **OAuth client ID**
3. **Application type:** Web application
4. **Name:** `Genesis IAM` (or anything)
5. Under **Authorized redirect URIs**, click **+ Add URI** and enter:
   ```
   http://localhost:8000/auth/sso/google/callback
   ```
   For production, add your real domain:
   ```
   https://auth.yourdomain.com/auth/sso/google/callback
   ```
6. Click **Create**

## Step 4: Copy Credentials

A dialog shows your credentials:
- **Client ID:** `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret:** `GOCSPX-xxxxxxxxxxxxx`

Copy both values.

## Step 5: Configure Genesis

Add to your `docker-compose.yml` environment section (or `.env` file):

```yaml
GOOGLE_CLIENT_ID: "123456789-abcdef.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET: "GOCSPX-xxxxxxxxxxxxx"
```

Restart the API:
```bash
docker compose up -d api
```

## Step 6: Test

1. Verify Google is listed:
   ```bash
   curl http://localhost:8001/auth/sso/providers
   # Should include "google"
   ```

2. Open in your browser:
   ```
   http://localhost:8001/auth/sso/google/authorize
   ```

3. You should be redirected to Google's login page
4. After signing in, Google redirects back to Genesis
5. Genesis returns JWT tokens (or redirects to your frontend with tokens)

---

## Notes

- **Testing mode:** While the consent screen is in "Testing" status, only test users you added can log in. To allow any Google account, publish the app (may require Google review).
- **Redirect URI must match exactly:** The URI in Google Console must match `{OAUTH_ISSUER}/auth/sso/google/callback`. If `OAUTH_ISSUER` is `http://localhost:8000`, the redirect URI must be `http://localhost:8000/auth/sso/google/callback`.
- **Scopes:** Genesis requests `openid email profile` from Google. This returns the user's email, name, and profile picture.

## What Genesis Receives from Google

```json
{
  "sub": "1234567890",
  "email": "user@gmail.com",
  "email_verified": true,
  "name": "Jane Doe",
  "given_name": "Jane",
  "family_name": "Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

Genesis uses this to create or link the user account and populate the profile.
