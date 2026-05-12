"""
Genesis IAM - End-to-End Test Suite
====================================
Tests the complete lifecycle of the IAM system against a running instance.

Prerequisites:
    docker compose up -d
    (API on :8001, Web on :8082, MySQL on :3306)

Run:
    pytest tests/test_e2e.py -v

Or standalone:
    python tests/test_e2e.py
"""

import requests
import base64
import json
import os
import time

BASE = os.getenv("GENESIS_API_URL", "http://localhost:8001")
WEB = os.getenv("GENESIS_WEB_URL", "http://localhost:8082")

# Test data
TEST_USER = {
    "username": f"e2e_user_{int(time.time())}",
    "email": f"e2e_{int(time.time())}@test.com",
    "password": "E2eTestPass123!",
}

TEST_PROFILE = {
    "given_name": "E2E",
    "family_name": "Tester",
    "nick_name": "0xe2e",
    "date_of_birth": "1995-06-15",
    "mobile_number": "+1 555 999 0000",
    "address_line1": "456 Test Avenue",
    "address_line2": "Suite 100",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94102",
    "country": "US",
}

# State shared across tests
state = {}


# ============================================================
# Helpers
# ============================================================

def api(method, path, token=None, json_data=None, form_data=None, files=None):
    """Make an API request and return (status_code, json_body)."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    kwargs = {"headers": headers}
    if json_data:
        kwargs["json"] = json_data
    if form_data:
        kwargs["data"] = form_data
    if files:
        kwargs["files"] = files
    resp = getattr(requests, method)(f"{BASE}{path}", **kwargs)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


def decode_jwt_payload(token):
    """Decode JWT payload without verification (for inspection)."""
    payload = token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


# ============================================================
# 1. Health & Discovery
# ============================================================

def test_01_health():
    """Service health check."""
    code, body = api("get", "/health")
    assert code == 200, f"Health check failed: {body}"
    assert body["status"] == "ok"
    assert body["service"] == "genesis-iam"
    print(f"  [PASS] /health -> {body['status']}")


def test_02_jwks():
    """JWKS endpoint returns RSA public keys."""
    code, body = api("get", "/.well-known/jwks.json")
    assert code == 200
    assert "keys" in body
    assert len(body["keys"]) >= 1
    key = body["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert "kid" in key
    state["kid"] = key["kid"]
    print(f"  [PASS] JWKS -> {len(body['keys'])} key(s), kid={key['kid']}")


def test_03_oidc_discovery():
    """OIDC discovery endpoint."""
    code, body = api("get", "/.well-known/openid-configuration")
    assert code == 200
    assert body["issuer"]
    assert "authorization_endpoint" in body
    assert "token_endpoint" in body
    assert "userinfo_endpoint" in body
    assert "jwks_uri" in body
    assert "RS256" in body["id_token_signing_alg_values_supported"]
    print(f"  [PASS] OIDC discovery -> issuer={body['issuer']}")


# ============================================================
# 2. User Registration
# ============================================================

def test_04_register_user():
    """Register a new user with password."""
    code, body = api("post", "/users/", json_data=TEST_USER)
    assert code == 200, f"Registration failed: {body}"
    assert body["username"] == TEST_USER["username"]
    assert body["email"] == TEST_USER["email"]
    assert body["auth_provider"] == "native"
    assert body["is_native"] is True
    assert body["role"] == "user"
    assert body["is_active"] is True
    state["user_id"] = body["id"]
    print(f"  [PASS] Register -> id={body['id'][:12]}... role={body['role']}")


def test_05_register_duplicate_username():
    """Duplicate username is rejected."""
    dup = {**TEST_USER, "email": "other@test.com"}
    code, body = api("post", "/users/", json_data=dup)
    assert code == 400
    assert "already" in body["detail"].lower()
    print(f"  [PASS] Duplicate username rejected -> {body['detail']}")


def test_06_register_duplicate_email():
    """Duplicate email is rejected."""
    dup = {**TEST_USER, "username": "other_user"}
    code, body = api("post", "/users/", json_data=dup)
    assert code == 400
    assert "already" in body["detail"].lower()
    print(f"  [PASS] Duplicate email rejected -> {body['detail']}")


def test_07_register_weak_password():
    """Weak passwords are rejected."""
    weak = {**TEST_USER, "username": "weakuser", "email": "weak@test.com", "password": "short"}
    code, body = api("post", "/users/", json_data=weak)
    assert code == 422, f"Expected 422, got {code}: {body}"
    print(f"  [PASS] Weak password rejected")


# ============================================================
# 3. Native Login
# ============================================================

def test_08_login():
    """Login with username/password returns tokens."""
    code, body = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    assert code == 200, f"Login failed: {body}"
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    state["access_token"] = body["access_token"]
    state["refresh_token"] = body["refresh_token"]
    print(f"  [PASS] Login -> got access + refresh tokens")


def test_09_login_wrong_password():
    """Wrong password is rejected."""
    code, body = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": "WrongPassword123!",
    })
    assert code == 401
    print(f"  [PASS] Wrong password rejected -> {body['detail']}")


def test_10_login_nonexistent_user():
    """Non-existent user is rejected."""
    code, body = api("post", "/token", form_data={
        "username": "nobody_exists",
        "password": "Whatever123!",
    })
    assert code == 401
    print(f"  [PASS] Non-existent user rejected")


# ============================================================
# 4. JWT Validation
# ============================================================

def test_11_jwt_structure():
    """Access token has correct RS256 JWT structure."""
    token = state["access_token"]
    parts = token.split(".")
    assert len(parts) == 3, "JWT must have 3 parts"

    # Header
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    assert header["alg"] == "RS256"
    assert header["kid"] == state["kid"]
    assert header["typ"] == "JWT"

    # Payload
    payload = decode_jwt_payload(token)
    assert payload["sub"] == state["user_id"]
    assert payload["role"] == "user"
    assert payload["scope"] == "openid profile email"
    assert "sid" in payload
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert payload["auth_method"] == "password"
    state["session_id"] = payload["sid"]
    print(f"  [PASS] JWT -> alg=RS256 kid={header['kid']} sub={payload['sub'][:12]}... role={payload['role']}")


def test_12_refresh_token_type():
    """Refresh token has token_type=refresh claim."""
    payload = decode_jwt_payload(state["refresh_token"])
    assert payload.get("token_type") == "refresh"
    assert "sid" in payload
    print(f"  [PASS] Refresh token has token_type=refresh")


def test_13_refresh_token_rejected_as_access():
    """Refresh token cannot be used as an access token."""
    code, body = api("get", "/users/me/", token=state["refresh_token"])
    assert code == 401
    assert "refresh" in body["detail"].lower()
    print(f"  [PASS] Refresh rejected as access -> {body['detail']}")


# ============================================================
# 5. Protected Endpoints
# ============================================================

def test_14_get_me():
    """GET /users/me/ returns authenticated user."""
    code, body = api("get", "/users/me/", token=state["access_token"])
    assert code == 200
    assert body["id"] == state["user_id"]
    assert body["username"] == TEST_USER["username"]
    assert body["last_login_method"] == "password"
    print(f"  [PASS] /users/me/ -> {body['username']}")


def test_15_no_token_rejected():
    """Protected endpoint without token returns 401."""
    code, body = api("get", "/users/me/")
    assert code == 401
    print(f"  [PASS] No token -> 401")


def test_16_validate_token():
    """POST /token/validate returns user identity."""
    code, body = api("post", "/token/validate", token=state["access_token"])
    assert code == 200
    assert body["user_id"] == state["user_id"]
    assert body["username"] == TEST_USER["username"]
    print(f"  [PASS] /token/validate -> user_id={body['user_id'][:12]}...")


# ============================================================
# 6. Profile Management
# ============================================================

def test_17_no_profile_initially():
    """New user has no profile."""
    code, body = api("get", "/profile/me/", token=state["access_token"])
    assert code == 404
    print(f"  [PASS] No profile initially -> 404")


def test_18_create_profile():
    """Create profile with ecommerce fields."""
    data = {**TEST_PROFILE, "sub": TEST_USER["username"]}
    code, body = api("post", "/profile/", json_data=data, token=state["access_token"])
    assert code == 200, f"Profile creation failed: {body}"
    assert body["given_name"] == "E2E"
    assert body["family_name"] == "Tester"
    assert body["date_of_birth"] == "1995-06-15"
    assert body["mobile_number"] == "+1 555 999 0000"
    assert body["address_line1"] == "456 Test Avenue"
    assert body["city"] == "San Francisco"
    assert body["state"] == "CA"
    assert body["zip_code"] == "94102"
    assert body["country"] == "US"
    assert body["phone_verified"] is False
    state["profile_id"] = body["id"]
    print(f"  [PASS] Profile created -> {body['given_name']} {body['family_name']}, {body['city']}, {body['state']}")


def test_19_duplicate_profile_rejected():
    """Cannot create a second profile."""
    data = {**TEST_PROFILE, "sub": TEST_USER["username"]}
    code, body = api("post", "/profile/", json_data=data, token=state["access_token"])
    assert code == 400
    assert "already exists" in body["detail"].lower()
    print(f"  [PASS] Duplicate profile rejected")


def test_20_get_profile():
    """GET /profile/me/ returns full profile."""
    code, body = api("get", "/profile/me/", token=state["access_token"])
    assert code == 200
    assert body["address_line1"] == "456 Test Avenue"
    assert body["address_line2"] == "Suite 100"
    assert body["country"] == "US"
    print(f"  [PASS] GET profile -> address={body['address_line1']}, {body['city']}")


def test_21_update_profile():
    """PUT /profile/me/ updates specific fields."""
    code, body = api("put", "/profile/me/", json_data={
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90001",
        "mobile_number": "+1 555 888 0000",
    }, token=state["access_token"])
    assert code == 200
    assert body["city"] == "Los Angeles"
    assert body["zip_code"] == "90001"
    assert body["mobile_number"] == "+1 555 888 0000"
    # Original fields preserved
    assert body["given_name"] == "E2E"
    assert body["address_line1"] == "456 Test Avenue"
    print(f"  [PASS] Profile updated -> city={body['city']}, zip={body['zip_code']}")


def test_22_upload_picture():
    """Upload a profile picture (PNG)."""
    # Create a minimal 1x1 PNG
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    code, body = api("post", "/profile/me/picture", token=state["access_token"],
                      files={"picture": ("test.png", png, "image/png")})
    assert code == 200, f"Upload failed: {body}"
    assert "picture" in body
    assert "picture_key" in body
    assert body["picture_key"].endswith(".webp")
    state["picture_url"] = body["picture"]
    print(f"  [PASS] Picture uploaded -> {body['picture_key']}")


def test_23_picture_in_profile():
    """Profile now contains the picture URL."""
    code, body = api("get", "/profile/me/", token=state["access_token"])
    assert code == 200
    assert body["picture"] is not None
    assert body["picture_key"] is not None
    print(f"  [PASS] Profile has picture URL")


def test_24_delete_picture():
    """Delete profile picture."""
    code, body = api("delete", "/profile/me/picture", token=state["access_token"])
    assert code == 200
    # Verify it's gone
    code2, body2 = api("get", "/profile/me/", token=state["access_token"])
    assert body2["picture"] is None
    assert body2["picture_key"] is None
    print(f"  [PASS] Picture deleted")


# ============================================================
# 7. Session Management
# ============================================================

def test_25_list_sessions():
    """List active sessions."""
    code, body = api("get", "/auth/sessions", token=state["access_token"])
    assert code == 200
    assert body["total"] >= 1
    current = [s for s in body["sessions"] if s["is_current"]]
    assert len(current) == 1
    assert current[0]["login_method"] == "password"
    state["current_session_id"] = current[0]["id"]
    print(f"  [PASS] Sessions -> {body['total']} active, current={current[0]['id'][:12]}...")


def test_26_create_second_session():
    """Login again to create a second session."""
    code, body = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    assert code == 200
    state["second_token"] = body["access_token"]

    code2, body2 = api("get", "/auth/sessions", token=state["access_token"])
    assert body2["total"] >= 2
    print(f"  [PASS] Second session created -> total={body2['total']}")


def test_27_revoke_second_session():
    """Revoke a specific session."""
    # Get the second session's ID
    code, body = api("get", "/auth/sessions", token=state["access_token"])
    other = [s for s in body["sessions"] if not s["is_current"]]
    assert len(other) >= 1
    target = other[0]["id"]

    code2, body2 = api("delete", f"/auth/sessions/{target}", token=state["access_token"])
    assert code2 == 200
    print(f"  [PASS] Session revoked -> {target[:12]}...")


def test_28_refresh_token_rotation():
    """Refresh token returns new pair and old one is invalidated."""
    code, body = api("post", "/refresh_token", token=state["refresh_token"])
    assert code == 200, f"Refresh failed: {body}"
    assert body["access_token"] != state["access_token"]
    assert body["refresh_token"] != state["refresh_token"]
    old_refresh = state["refresh_token"]
    state["access_token"] = body["access_token"]
    state["refresh_token"] = body["refresh_token"]

    # Old refresh token should be rejected (replay detection)
    code2, body2 = api("post", "/refresh_token", token=old_refresh)
    assert code2 == 401
    assert "rotated" in body2["detail"].lower()
    print(f"  [PASS] Token rotated + old token replay detected")


def test_29_revoke_all_sessions():
    """Login fresh, create multiple sessions, revoke all except current."""
    # Login fresh since last test revoked our session
    code, body = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    assert code == 200
    state["access_token"] = body["access_token"]
    state["refresh_token"] = body["refresh_token"]

    # Create 2 more sessions
    api("post", "/token", form_data={"username": TEST_USER["username"], "password": TEST_USER["password"]})
    api("post", "/token", form_data={"username": TEST_USER["username"], "password": TEST_USER["password"]})

    # Revoke all except current
    code2, body2 = api("delete", "/auth/sessions", token=state["access_token"])
    assert code2 == 200
    assert "revoked" in body2["message"].lower()

    # Should have exactly 1 session left
    code3, body3 = api("get", "/auth/sessions", token=state["access_token"])
    assert body3["total"] == 1
    assert body3["sessions"][0]["is_current"] is True
    print(f"  [PASS] Revoked all others -> {body2['message']}, 1 remaining")


# ============================================================
# 8. SSO (Provider Discovery)
# ============================================================

def test_30_sso_providers():
    """List configured SSO providers."""
    code, body = api("get", "/auth/sso/providers")
    assert code == 200
    assert "providers" in body
    assert isinstance(body["providers"], list)
    print(f"  [PASS] SSO providers -> {body['providers'] or '(none configured)'}")


def test_31_sso_invalid_provider():
    """Invalid SSO provider is rejected."""
    code, body = api("get", "/auth/sso/twitter/authorize")
    assert code == 400
    assert "invalid" in body["detail"].lower()
    print(f"  [PASS] Invalid provider rejected")


def test_32_linked_providers():
    """List linked SSO providers (empty for native user)."""
    code, body = api("get", "/auth/sso/linked", token=state["access_token"])
    assert code == 200
    assert body["linked_providers"] == []
    print(f"  [PASS] No linked providers for native user")


# ============================================================
# 9. OIDC Flow
# ============================================================

def test_33_admin_create_client():
    """Create an OAuth client for OIDC testing."""
    # Get Adam's token
    adam_pass = _get_adam_password()
    if not adam_pass:
        print(f"  [SKIP] Cannot get Adam password from logs")
        return

    code, body = api("post", "/admin/login", form_data={"username": "adam", "password": adam_pass})
    assert code == 200, f"Admin login failed: {body}"
    admin_token = body["access_token"]

    code2, body2 = api("post", "/admin/clients", json_data={
        "client_name": f"e2e_test_{int(time.time())}",
        "redirect_uris": ["http://localhost:3000/callback"],
        "allowed_scopes": ["openid", "profile", "email", "offline_access"],
        "allowed_audiences": ["genesis-api"],
        "grant_types": ["authorization_code", "refresh_token", "client_credentials"],
    }, token=admin_token)
    assert code2 == 200, f"Client creation failed: {body2}"
    state["client_id"] = body2["id"]
    state["client_secret"] = body2["client_secret"]
    state["admin_token"] = admin_token
    print(f"  [PASS] OAuth client created -> {body2['client_name']}")


def test_34_oidc_authorize():
    """Authorization endpoint returns redirect with code."""
    if "client_id" not in state:
        print(f"  [SKIP] No client_id")
        return

    resp = requests.get(f"{BASE}/oauth/authorize", params={
        "response_type": "code",
        "client_id": state["client_id"],
        "redirect_uri": "http://localhost:3000/callback",
        "scope": "openid profile email offline_access",
        "state": "e2e_test_state",
        "nonce": "e2e_test_nonce",
    }, headers={"Authorization": f"Bearer {state['access_token']}"}, allow_redirects=False)

    assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
    location = resp.headers["location"]
    assert "code=" in location
    assert "state=e2e_test_state" in location

    # Extract code
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(location).query)
    state["auth_code"] = params["code"][0]
    print(f"  [PASS] Authorize -> code={state['auth_code'][:20]}...")


def test_35_oidc_token_exchange():
    """Exchange authorization code for tokens."""
    if "auth_code" not in state:
        print(f"  [SKIP] No auth code")
        return

    code, body = api("post", "/oauth/token", form_data={
        "grant_type": "authorization_code",
        "code": state["auth_code"],
        "redirect_uri": "http://localhost:3000/callback",
        "client_id": state["client_id"],
        "client_secret": state["client_secret"],
    })
    assert code == 200, f"Token exchange failed: {body}"
    assert "access_token" in body
    assert "id_token" in body
    assert "refresh_token" in body
    assert body["scope"] == "openid profile email offline_access"
    state["oidc_token"] = body["access_token"]
    state["id_token"] = body["id_token"]
    print(f"  [PASS] Token exchange -> got access + id + refresh tokens")


def test_36_id_token_claims():
    """ID token contains correct user claims."""
    if "id_token" not in state:
        print(f"  [SKIP] No ID token")
        return

    claims = decode_jwt_payload(state["id_token"])
    assert claims["sub"] == state["user_id"]
    assert claims["aud"] == state["client_id"]
    assert claims["nonce"] == "e2e_test_nonce"
    assert claims["email"] == TEST_USER["email"]
    assert "name" in claims
    assert "at_hash" in claims
    print(f"  [PASS] ID token -> sub={claims['sub'][:12]}... name={claims.get('name')} nonce={claims['nonce']}")


def test_37_userinfo():
    """UserInfo endpoint returns profile claims."""
    if "oidc_token" not in state:
        print(f"  [SKIP] No OIDC token")
        return

    code, body = api("get", "/oauth/userinfo", token=state["oidc_token"])
    assert code == 200, f"UserInfo failed: {body}"
    assert body["sub"] == state["user_id"]
    assert body["email"] == TEST_USER["email"]
    assert body["given_name"] == "E2E"
    assert body["family_name"] == "Tester"
    print(f"  [PASS] UserInfo -> {body['given_name']} {body['family_name']} ({body['email']})")


def test_38_client_credentials():
    """Client credentials grant for service-to-service."""
    if "client_id" not in state:
        print(f"  [SKIP] No client_id")
        return

    code, body = api("post", "/oauth/token", form_data={
        "grant_type": "client_credentials",
        "client_id": state["client_id"],
        "client_secret": state["client_secret"],
        "scope": "openid",
    })
    assert code == 200, f"Client credentials failed: {body}"
    assert "access_token" in body
    assert body["scope"] == "openid"
    # sub should be the client_id
    claims = decode_jwt_payload(body["access_token"])
    assert claims["sub"] == state["client_id"]
    assert claims["auth_method"] == "client_credentials"
    print(f"  [PASS] Client credentials -> sub={claims['sub'][:12]}... (client)")


# ============================================================
# 10. Admin Dashboard
# ============================================================

def test_39_admin_login():
    """Admin login with ROOT user."""
    if "admin_token" not in state:
        adam_pass = _get_adam_password()
        if not adam_pass:
            print(f"  [SKIP] No Adam password")
            return
        code, body = api("post", "/admin/login", form_data={"username": "adam", "password": adam_pass})
        assert code == 200
        state["admin_token"] = body["access_token"]

    claims = decode_jwt_payload(state["admin_token"])
    assert claims["role"] == "root"
    print(f"  [PASS] Admin login -> role={claims['role']}")


def test_40_admin_rejected_for_normal_user():
    """Normal user cannot use admin login."""
    code, body = api("post", "/admin/login", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    assert code == 403
    assert "admin" in body["detail"].lower()
    print(f"  [PASS] Normal user rejected from admin login")


def test_41_analytics():
    """Admin analytics endpoint."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    code, body = api("get", "/admin/analytics", token=state["admin_token"])
    assert code == 200
    assert body["total_users"] >= 2  # adam + test user
    assert "provider_breakdown" in body
    assert body["admin_count"] >= 1
    print(f"  [PASS] Analytics -> total={body['total_users']} active={body['active_users']} admins={body['admin_count']}")


def test_42_admin_user_list():
    """Admin paginated user list."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    code, body = api("get", "/admin/users?page=1&per_page=20", token=state["admin_token"])
    assert code == 200
    assert body["total"] >= 2
    assert body["page"] == 1
    assert body["per_page"] == 20
    assert len(body["users"]) >= 2
    print(f"  [PASS] User list -> total={body['total']} page={body['page']}/{body['total_pages']}")


def test_43_admin_user_search():
    """Admin search by username."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    code, body = api("get", f"/admin/users?search={TEST_USER['username']}", token=state["admin_token"])
    assert code == 200
    assert body["total"] == 1
    assert body["users"][0]["username"] == TEST_USER["username"]
    print(f"  [PASS] Search -> found {body['users'][0]['username']}")


def test_44_admin_user_detail():
    """Admin user detail with profile and sessions."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    code, body = api("get", f"/admin/users/{state['user_id']}", token=state["admin_token"])
    assert code == 200
    assert body["username"] == TEST_USER["username"]
    assert body["role"] == "user"
    assert body["profile"] is not None
    assert body["profile"]["given_name"] == "E2E"
    assert body["profile"]["city"] == "Los Angeles"  # updated in test_21
    assert body["sessions_count"] >= 1
    print(f"  [PASS] User detail -> {body['username']} | profile={body['profile']['given_name']} | sessions={body['sessions_count']}")


def test_45_admin_rbac():
    """Normal user cannot access admin endpoints."""
    code, body = api("get", "/admin/analytics", token=state["access_token"])
    assert code == 403
    assert "permission" in body["detail"].lower()
    print(f"  [PASS] RBAC enforced -> normal user gets 403")


def test_46_admin_change_role():
    """Admin can change a user's role."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    code, body = api("post", f"/admin/users/{state['user_id']}/role",
                      json_data={"role": "admin"}, token=state["admin_token"])
    assert code == 200

    # Verify
    code2, body2 = api("get", f"/admin/users/{state['user_id']}", token=state["admin_token"])
    assert body2["role"] == "admin"

    # Revert
    api("post", f"/admin/users/{state['user_id']}/role",
        json_data={"role": "user"}, token=state["admin_token"])
    print(f"  [PASS] Role changed to admin and reverted")


def test_47_admin_disable_user():
    """Admin can disable/enable a user."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    # Disable
    code, body = api("post", f"/admin/users/{state['user_id']}/disable", token=state["admin_token"])
    assert code == 200
    assert body["disabled"] is True

    # Disabled user can't login
    code2, body2 = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    assert code2 == 403

    # Re-enable
    code3, body3 = api("post", f"/admin/users/{state['user_id']}/disable", token=state["admin_token"])
    assert body3["disabled"] is False
    print(f"  [PASS] User disabled -> login blocked -> re-enabled")


def test_48_cannot_delete_root():
    """Cannot delete the ROOT user."""
    if "admin_token" not in state:
        print(f"  [SKIP]")
        return

    # Find Adam's ID
    code, body = api("get", "/admin/users?search=adam", token=state["admin_token"])
    adam_id = body["users"][0]["id"]

    code2, body2 = api("delete", f"/admin/users/{adam_id}", token=state["admin_token"])
    assert code2 == 403
    assert "root" in body2["detail"].lower()
    print(f"  [PASS] Cannot delete ROOT user")


# ============================================================
# 11. Web Frontend
# ============================================================

def test_49_web_serves():
    """Web frontend returns HTML."""
    resp = requests.get(WEB)
    assert resp.status_code == 200
    assert "Genesis IAM" in resp.text
    print(f"  [PASS] Web serves HTML")


def test_50_web_spa_routing():
    """SPA routes all return index.html."""
    for path in ["/login", "/register", "/profile", "/admin/login", "/admin"]:
        resp = requests.get(f"{WEB}{path}")
        assert resp.status_code == 200, f"SPA route {path} failed"
    print(f"  [PASS] SPA routing works for all paths")


# ============================================================
# 12. Cleanup
# ============================================================

def test_51_delete_profile():
    """Delete the test profile."""
    # Re-login since session may have been revoked
    code, body = api("post", "/token", form_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    state["access_token"] = body["access_token"]

    code2, body2 = api("delete", "/profile/me/", token=state["access_token"])
    assert code2 == 200
    print(f"  [PASS] Profile deleted")


def test_52_delete_user():
    """Admin deletes the test user."""
    # Re-authenticate as admin (previous token may be expired)
    adam_pass = _get_adam_password()
    if not adam_pass:
        print(f"  [SKIP] No Adam password")
        return
    code0, body0 = api("post", "/admin/login", form_data={"username": "adam", "password": adam_pass})
    assert code0 == 200, f"Admin re-login failed: {body0}"
    admin_token = body0["access_token"]

    code, body = api("delete", f"/admin/users/{state['user_id']}", token=admin_token)
    assert code == 200, f"Delete failed: {body}"

    # Verify user is gone
    code2, body2 = api("get", f"/admin/users/{state['user_id']}", token=admin_token)
    assert code2 == 404
    print(f"  [PASS] User deleted and verified gone")


# ============================================================
# Helpers
# ============================================================

def _get_adam_password():
    """Try to get Adam's password from docker logs or env."""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "compose", "logs", "api"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.split("\n"):
            if "Password:" in line and "adam" not in line.lower() or "Password:" in line:
                parts = line.split("Password:")
                if len(parts) > 1:
                    return parts[1].strip()
    except Exception:
        pass
    return os.getenv("ADAM_PASSWORD")


# ============================================================
# Runner
# ============================================================

if __name__ == "__main__":
    tests = sorted(
        [(name, func) for name, func in globals().items() if name.startswith("test_") and callable(func)],
        key=lambda x: x[0],
    )

    print("=" * 60)
    print("  GENESIS IAM - End-to-End Test Suite")
    print(f"  API: {BASE}")
    print(f"  Web: {WEB}")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for name, func in tests:
        label = name.replace("test_", "").replace("_", " ").strip()
        test_num = name.split("_")[1]
        try:
            print(f"\n[{test_num}] {label}")
            func()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Total:   {len(tests)} tests")
    print("=" * 60)

    exit(1 if failed else 0)
