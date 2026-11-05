from datetime import datetime, timedelta


def admin_headers(client, admin):
    response = client.post("/admin/login", data={"username": admin.username, "password": "ValidPassword123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def usernames(client, headers, query):
    response = client.get(f"/admin/users?{query}", headers=headers)
    assert response.status_code == 200, response.text
    return [u["username"] for u in response.json()["users"]]


def test_admin_user_list_filters_by_role_status_and_provider(client, make_user):
    admin = make_user(role="admin")
    disabled = make_user(disabled=True)
    github = make_user(auth_provider="github", is_native=False)
    headers = admin_headers(client, admin)

    assert usernames(client, headers, "role=admin") == [admin.username]
    assert usernames(client, headers, "status=disabled") == [disabled.username]
    assert disabled.username not in usernames(client, headers, "status=active")
    assert usernames(client, headers, "provider=github") == [github.username]
    assert usernames(client, headers, "role=user&provider=github") == [github.username]


def test_admin_user_list_sorts_by_last_login_and_rejects_unknown_filters(client, make_user):
    admin = make_user(role="admin")
    now = datetime.utcnow()
    older = make_user(last_login_at=now - timedelta(days=2))
    newer = make_user(last_login_at=now - timedelta(hours=1))
    make_user()  # never signed in: left out of the last-login ordering
    headers = admin_headers(client, admin)

    ordered = usernames(client, headers, "sort=last_login")
    assert ordered.index(newer.username) < ordered.index(older.username)
    assert len(ordered) == 3  # newer, older and the admin who just signed in

    for query in ("role=superuser", "status=gone", "sort=name"):
        assert client.get(f"/admin/users?{query}", headers=headers).status_code == 422
