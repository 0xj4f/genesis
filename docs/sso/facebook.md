# Facebook SSO Setup

This guide walks through creating a Meta (Facebook) App so users can log into Genesis with their Facebook account.

---

## Step 1: Create a Meta Developer Account

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. If you don't have a developer account, click **Get Started** and follow the registration
3. You need a verified Facebook account

## Step 2: Create an App

1. Go to [My Apps](https://developers.facebook.com/apps/)
2. Click **Create App**
3. Select a use case:
   - Choose **Authenticate and request data from users with Facebook Login**
   - Or **Other** > **Consumer** if the above isn't shown
4. **App name:** `Genesis IAM` (or your project name)
5. **App contact email:** Your email
6. Click **Create App**

## Step 3: Set Up Facebook Login

1. In your app dashboard, find **Facebook Login** and click **Set Up**
2. Choose **Web** as the platform
3. **Site URL:** `http://localhost:8001` (or your production URL)
4. Click **Save**, then click **Continue** through the quickstart (you can skip it)

## Step 4: Configure Redirect URIs

1. In the left sidebar, go to **Facebook Login** > **Settings**
2. Under **Valid OAuth Redirect URIs**, add:
   ```
   http://localhost:8000/auth/sso/facebook/callback
   ```
   For production:
   ```
   https://auth.yourdomain.com/auth/sso/facebook/callback
   ```
3. Click **Save Changes**

## Step 5: Copy Credentials

1. In the left sidebar, go to **App Settings** > **Basic**
2. Copy the **App ID** (this is your client ID)
3. Click **Show** next to **App Secret** (enter your Facebook password)
4. Copy the **App Secret** (this is your client secret)

## Step 6: Configure Genesis

Add to your `docker-compose.yml` environment section (or `.env` file):

```yaml
FACEBOOK_CLIENT_ID: "123456789012345"
FACEBOOK_CLIENT_SECRET: "abcdef0123456789abcdef0123456789"
```

Restart the API:
```bash
docker compose up -d api
```

## Step 7: Test

1. Verify Facebook is listed:
   ```bash
   curl http://localhost:8001/auth/sso/providers
   # Should include "facebook"
   ```

2. Open in your browser:
   ```
   http://localhost:8001/auth/sso/facebook/authorize
   ```

3. You'll see Facebook's login/authorization dialog
4. After authorizing, Facebook redirects back to Genesis
5. Genesis returns JWT tokens

---

## Important: App Modes

Facebook has two modes for apps:

### Development Mode (Default)
- Only **app admins, developers, and testers** can log in
- To add test users: **App Roles** > **Roles** > add users
- Good for development and testing

### Live Mode (Production)
- Any Facebook user can log in
- To switch: go to the app dashboard top bar and toggle **App Mode** from "Development" to "Live"
- **Requirements for Live Mode:**
  - Privacy Policy URL must be set (App Settings > Basic)
  - App must pass App Review for `email` and `public_profile` permissions (usually auto-approved for basic permissions)
  - Terms of Service URL (recommended)

For local development and testing, Development Mode is fine.

## Step 8: Add Test Users (Development Mode)

If you're in Development Mode and want other people to test:

1. Go to **App Roles** > **Roles**
2. Click **Add Testers**
3. Enter the Facebook username or email of the person
4. They must accept the invitation from their Facebook notifications

---

## Notes

- **Permissions:** Genesis requests `email` and `public_profile` scopes. These are the most basic and usually don't require App Review.
- **Profile picture:** Facebook returns a picture URL via the Graph API. Genesis stores it in the profile's `picture` field.
- **Callback URL must match exactly:** Including protocol and path. `http` vs `https` matters.
- **HTTPS requirement:** For production (Live Mode), Facebook requires HTTPS redirect URIs. `http://localhost` is allowed for development.

## What Genesis Receives from Facebook

```json
{
  "id": "10229876543210",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "picture": {
    "data": {
      "url": "https://platform-lookaside.fbsbx.com/platform/profilepic/..."
    }
  }
}
```

- `id` is used as `provider_user_id`
- `name` is split into `given_name` / `family_name`
- `picture.data.url` is set as the profile picture
- Facebook does not return `email_verified` separately; Genesis treats provided emails as verified
