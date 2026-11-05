from datetime import datetime, timedelta

from app.models.account_request_db_model import AccountRequest
from app.models.user_api_model import validate_password_strength
from app.models.user_db_model import User


def bearer(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def admin_headers(client, admin):
    response = client.post("/admin/login", data={"username": admin.username, "password": "ValidPassword123!"})
    assert response.status_code == 200, response.text
    return bearer(response.json())


def sign_in(client, username, password):
    return client.post("/token", data={"username": username, "password": password})


def create_user(client, headers, **body):
    body = {"username": "new_hire", "email": "new_hire@example.com", **body}
    return client.post("/admin/users", headers=headers, json=body)


def test_admin_creates_user_with_generated_temporary_password(client, make_user, db):
    headers = admin_headers(client, make_user(role="admin"))

    response = create_user(client, headers)
    assert response.status_code == 201, response.text
    body = response.json()
    validate_password_strength(body["temporary_password"])
    assert body["must_change_password"] is True
    assert body["user"]["username"] == "new_hire"

    user = db.query(User).filter(User.username == "new_hire").one()
    assert user.must_change_password and not user.email_verified
    assert timedelta(hours=71) < user.password_expires_at - datetime.utcnow() <= timedelta(hours=72)


def test_admin_set_password_can_be_permanent(client, make_user):
    headers = admin_headers(client, make_user(role="admin"))
    response = create_user(client, headers, password="ChosenPassword123!", require_password_change=False)
    assert response.status_code == 201, response.text
    assert response.json()["temporary_password"] is None
    assert response.json()["must_change_password"] is False
    tokens = sign_in(client, "new_hire", "ChosenPassword123!").json()
    assert client.get("/profile/me/", headers=bearer(tokens)).status_code == 404  # usable, just no profile yet


def test_creation_roles_follow_policy(client, make_user):
    admin_headers_ = admin_headers(client, make_user(role="admin"))
    root_headers = admin_headers(client, make_user(role="root"))

    assert create_user(client, admin_headers_, role="admin").status_code == 403
    assert create_user(client, root_headers, role="root").status_code == 422
    assert create_user(client, root_headers, role="admin").status_code == 201
    assert create_user(client, root_headers, username="other").status_code == 400  # email taken


def test_temporary_password_only_allows_changing_it(client, make_user):
    headers = admin_headers(client, make_user(role="admin"))
    temporary = create_user(client, headers).json()["temporary_password"]

    tokens = sign_in(client, "new_hire", temporary).json()
    auth = bearer(tokens)
    blocked = client.get("/profile/me/", headers=auth)
    assert blocked.status_code == 403 and blocked.json()["detail"] == "Password change required"
    assert client.get("/auth/sessions", headers=auth).status_code == 403
    me = client.get("/users/me/", headers=auth)
    assert me.status_code == 200 and me.json()["must_change_password"] is True

    changed = client.post("/users/me/password", headers=auth,
                          json={"current_password": temporary, "new_password": "MyOwnPassword123!"})
    assert changed.status_code == 200, changed.text
    assert client.get("/users/me/", headers=auth).json()["must_change_password"] is False
    # The token issued with the temporary password stays restricted; a refresh replaces it.
    assert client.get("/profile/me/", headers=auth).status_code == 403
    refreshed = client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert refreshed.status_code == 200, refreshed.text
    assert client.get("/profile/me/", headers=bearer(refreshed.json())).status_code == 404
    assert sign_in(client, "new_hire", temporary).status_code == 401


def test_temporary_admin_cannot_use_admin_api_until_changed(client, make_user):
    root_headers = admin_headers(client, make_user(role="root"))
    temporary = create_user(client, root_headers, role="admin").json()["temporary_password"]

    response = client.post("/admin/login", data={"username": "new_hire", "password": temporary})
    assert response.status_code == 200
    assert client.get("/admin/analytics", headers=bearer(response.json())).status_code == 403


def test_expired_temporary_password_is_refused(client, make_user, db):
    target = make_user()
    target.must_change_password = True
    target.password_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    response = sign_in(client, target.username, "ValidPassword123!")
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_admin_reset_generates_and_resolves_open_request(client, make_user, db):
    headers = admin_headers(client, make_user(role="admin"))
    target = make_user()
    client.post("/auth/password-reset-requests", json={"identifier": target.email})

    response = client.post(f"/admin/users/{target.id}/password", headers=headers, json={"generate": True})
    assert response.status_code == 200, response.text
    validate_password_strength(response.json()["temporary_password"])
    request = db.query(AccountRequest).filter(AccountRequest.user_id == str(target.id)).one()
    db.refresh(request)
    assert request.status == "resolved"

    both = client.post(f"/admin/users/{target.id}/password", headers=headers,
                       json={"generate": True, "new_password": "ChosenPassword123!"})
    assert both.status_code == 422


def test_reset_requests_do_not_reveal_accounts_and_are_deduplicated(client, make_user, db):
    target = make_user()
    root = make_user(role="root")

    unknown = client.post("/auth/password-reset-requests", json={"identifier": "nobody@example.com"})
    known = client.post("/auth/password-reset-requests", json={"identifier": target.username})
    again = client.post("/auth/password-reset-requests", json={"identifier": target.email})
    client.post("/auth/password-reset-requests", json={"identifier": root.username})

    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json() == again.json()
    rows = db.query(AccountRequest).all()
    assert len(rows) == 1
    assert rows[0].user_id == str(target.id) and rows[0].request_count == 2


def test_request_queue_visibility_and_actions(client, make_user, db):
    regular, admin_account = make_user(), make_user(role="admin")
    admin_h = admin_headers(client, make_user(role="admin"))
    root_h = admin_headers(client, make_user(role="root"))
    for account in (regular, admin_account):
        client.post("/auth/password-reset-requests", json={"identifier": account.username})

    def open_ids(headers):
        return {r["user"]["username"]: r["id"] for r in client.get("/admin/requests", headers=headers).json()["requests"]}

    assert set(open_ids(admin_h)) == {regular.username}
    assert set(open_ids(root_h)) == {regular.username, admin_account.username}
    assert client.get("/admin/requests/summary", headers=admin_h).json() == {"open": 1}

    admin_request = open_ids(root_h)[admin_account.username]
    assert client.post(f"/admin/requests/{admin_request}/temporary-password", headers=admin_h).status_code == 404

    issued = client.post(f"/admin/requests/{admin_request}/temporary-password", headers=root_h)
    assert issued.status_code == 200 and issued.json()["username"] == admin_account.username
    assert client.post(f"/admin/requests/{admin_request}/dismiss", headers=root_h).status_code == 409

    regular_request = open_ids(admin_h)[regular.username]
    assert client.post(f"/admin/requests/{regular_request}/dismiss", headers=admin_h).status_code == 200
    assert client.get("/admin/requests/summary", headers=root_h).json() == {"open": 0}
    resolved = client.get("/admin/requests?status=resolved", headers=root_h).json()["requests"]
    assert [r["user"]["username"] for r in resolved] == [admin_account.username]
    assert resolved[0]["resolved_by_username"]


def test_user_detail_shows_pending_reset(client, make_user):
    headers = admin_headers(client, make_user(role="admin"))
    target = make_user()
    client.post("/auth/password-reset-requests", json={"identifier": target.username})
    detail = client.get(f"/admin/users/{target.id}", headers=headers).json()
    assert detail["pending_request_id"] and detail["pending_password_reset_at"]
    assert detail["must_change_password"] is False


def decoded_claims(token):
    import jwt
    return jwt.decode(token, options={"verify_signature": False})


def test_temporary_password_tokens_are_restricted_everywhere(client, make_user):
    headers = admin_headers(client, make_user(role="admin"))
    temporary = create_user(client, headers).json()["temporary_password"]
    tokens = sign_in(client, "new_hire", temporary).json()

    claims = decoded_claims(tokens["access_token"])
    assert claims["aud"] == ["genesis-password-change"] and claims["scope"] == "password_change"
    # Relying parties and the internal-service check refuse it outright.
    assert client.post("/token/validate", headers=bearer(tokens)).status_code == 401
    assert client.get("/oauth/userinfo", headers=bearer(tokens)).status_code == 401

    # Refreshing before the change keeps it restricted.
    refreshed = client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).json()
    assert decoded_claims(refreshed["access_token"])["aud"] == ["genesis-password-change"]

    client.post("/users/me/password", headers=bearer(refreshed),
                json={"current_password": temporary, "new_password": "MyOwnPassword123!"})
    after = client.post("/refresh_token", headers={"Authorization": f"Bearer {refreshed['refresh_token']}"}).json()
    claims = decoded_claims(after["access_token"])
    assert "genesis-password-change" not in claims["aud"] and claims["scope"] == "openid profile email"


def test_temporary_password_cannot_be_kept(client, make_user):
    headers = admin_headers(client, make_user(role="admin"))
    temporary = create_user(client, headers).json()["temporary_password"]
    auth = bearer(sign_in(client, "new_hire", temporary).json())
    response = client.post("/users/me/password", headers=auth,
                           json={"current_password": temporary, "new_password": temporary})
    assert response.status_code == 400


def test_expired_temporary_password_does_not_reauthenticate(client, make_user, db):
    target = make_user()
    tokens = sign_in(client, target.username, "ValidPassword123!").json()
    target.must_change_password = True
    target.password_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    response = client.post("/users/me/password", headers=bearer(tokens),
                           json={"current_password": "ValidPassword123!", "new_password": "AnotherPassword123!"})
    assert response.status_code == 401


def test_email_like_identifier_prefers_the_email_owner(client, make_user, db):
    owner = make_user()
    squatter = make_user()
    squatter.username = owner.email  # a username that copies the owner's address
    db.commit()
    client.post("/auth/password-reset-requests", json={"identifier": owner.email})
    assert [r.user_id for r in db.query(AccountRequest).all()] == [str(owner.id)]


def test_single_request_lookup_and_dismiss_closes_all_open_rows(client, make_user, db):
    target, admin_account = make_user(), make_user(role="admin")
    admin_h = admin_headers(client, make_user(role="admin"))
    # Two open rows, as a race could leave.
    for _ in range(2):
        db.add(AccountRequest(user_id=str(target.id), category="password_reset", status="open"))
    db.add(AccountRequest(user_id=str(admin_account.id), category="password_reset", status="open"))
    db.commit()
    first, second, hidden = db.query(AccountRequest).all()

    assert client.get(f"/admin/requests/{first.id}", headers=admin_h).json()["user"]["username"] == target.username
    assert client.get(f"/admin/requests/{hidden.id}", headers=admin_h).status_code == 404

    assert client.post(f"/admin/requests/{first.id}/dismiss", headers=admin_h).status_code == 200
    db.expire_all()
    assert {r.status for r in db.query(AccountRequest).filter(AccountRequest.user_id == str(target.id))} == {"dismissed"}
