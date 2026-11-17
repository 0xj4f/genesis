"""Services sharing one Genesis: memberships, per-service roles and password policies (v0.4.0)."""

import jwt
import pytest
from pydantic import ValidationError

from app.config import ServiceDeclaration, Settings, get_settings
from app.models.service_db_model import ACTIVE, PENDING, SUSPENDED, Service, ServiceMembership
from app.models.session_db_model import Session as LoginSession
from app.models.user_db_model import User
from app.services.membership_service import sync_services

SHOP = "https://shop.test"
KITCHEN = "https://kitchen.test"
PASSWORD = "ValidPassword123!"  # the make_user fixture's password
BASIC_PASSWORD = "kusina88"


@pytest.fixture
def services(db, monkeypatch):
    settings = get_settings()
    declared = [
        ServiceDeclaration(client_id="shop", name="Shop", origins=[SHOP]),
        ServiceDeclaration(client_id="kitchen", name="Kitchen", origins=[KITCHEN], password_policy="basic"),
    ]
    monkeypatch.setattr(settings, "SERVICES", declared)
    sync_services(db)
    return declared


def origin(url):
    return {"Origin": url}


def register(client, url, username, password=BASIC_PASSWORD, **extra):
    body = {"username": username, "email": f"{username}@example.com", "password": password, **extra}
    return client.post("/users/", json=body, headers=origin(url) if url else {})


def sign_in(client, url, username, password=PASSWORD):
    return client.post("/token", data={"username": username, "password": password},
                       headers=origin(url) if url else {})


def bearer(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def claims(tokens):
    return jwt.decode(tokens["access_token"], options={"verify_signature": False})


def membership(db, user_id, service):
    db.expire_all()
    return db.query(ServiceMembership).filter_by(user_id=str(user_id), service_id=service).one_or_none()


def member(db, user, service, role="user", status=ACTIVE):
    row = membership(db, user.id, service)
    row = row or ServiceMembership(user_id=user.id, service_id=service, joined_via="admin")
    row.role, row.status = role, status
    db.add(row)
    db.commit()
    return row


# ---- configuration -------------------------------------------------------------------

def test_service_declarations_are_validated():
    shop = {"client_id": "shop", "name": "Shop", "origins": [SHOP]}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SERVICES=[shop, shop])
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SERVICES=[{**shop, "client_id": "genesis-api"}])
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SERVICES=[{**shop, "origins": [SHOP + "/path"]}])
    settings = Settings(_env_file=None, CORS_ALLOW_ORIGINS="https://console.test", SERVICES=[shop])
    assert settings.cors_origins == ["https://console.test", SHOP]


def test_sync_is_idempotent_and_backfills_pending_memberships(db, services, make_user, monkeypatch):
    user = make_user()
    root = make_user(role="root")
    sync_services(db)
    sync_services(db)
    assert db.query(ServiceMembership).filter_by(user_id=user.id).count() == 2
    assert membership(db, user.id, "kitchen").status == PENDING
    assert db.query(ServiceMembership).filter_by(user_id=root.id).count() == 0

    monkeypatch.setattr(get_settings(), "SERVICES", services[:1])
    sync_services(db)
    assert db.get(Service, "kitchen").is_active is False


# ---- which service is calling --------------------------------------------------------

def test_unknown_origin_is_refused_before_credentials(client, services, make_user):
    user = make_user()
    assert register(client, "https://evil.test", "mallory").status_code == 403
    assert sign_in(client, "https://evil.test", user.username, "wrong-password").status_code == 403


def test_client_id_must_match_the_origin(client, services, make_user):
    user = make_user()
    response = client.post("/token", data={"username": user.username, "password": PASSWORD, "client_id": "shop"},
                           headers=origin(KITCHEN))
    assert response.status_code == 400
    # Without a browser Origin, client_id names the service.
    tokens = client.post("/token", data={"username": user.username, "password": PASSWORD, "client_id": "kitchen"}).json()
    assert claims(tokens)["svc"] == "kitchen"


def test_no_origin_means_genesis_itself(client, services, make_user, login):
    tokens = login(make_user())
    assert claims(tokens)["aud"] == ["genesis-api"]
    assert "svc" not in claims(tokens)


# ---- registration --------------------------------------------------------------------

def test_signup_records_its_source_and_enrolls_everywhere(client, db, services):
    response = register(client, KITCHEN, "aling_nena")
    assert response.status_code == 200, response.text
    user = db.query(User).filter_by(username="aling_nena").one()
    assert user.registered_via == "kitchen"
    assert user.registration_ip
    kitchen, shop = membership(db, user.id, "kitchen"), membership(db, user.id, "shop")
    assert (kitchen.status, kitchen.joined_via) == (ACTIVE, "registration")
    assert (shop.status, shop.joined_via) == (PENDING, "auto")


def test_password_policy_follows_the_service(client, services):
    assert register(client, KITCHEN, "kitchen_user").status_code == 200
    strict = register(client, SHOP, "shop_user")
    assert strict.status_code == 422
    assert strict.json()["detail"][0]["loc"] == ["body", "password"]
    assert BASIC_PASSWORD not in strict.text
    for weak in ("kusina8", "kusinaaa", "88888888"):  # too short, no digit, no letter
        assert register(client, KITCHEN, f"weak_{len(weak)}_{weak[0]}", weak).status_code == 422


def test_login_never_rechecks_the_policy(client, services):
    register(client, KITCHEN, "carinderia")
    # Signed up with an 8-character password on the kitchen shop; it works on the shop too.
    assert sign_in(client, SHOP, "carinderia", BASIC_PASSWORD).status_code == 200


# ---- memberships, tokens and roles ---------------------------------------------------

def test_first_sign_in_activates_the_pending_membership(client, db, services):
    register(client, KITCHEN, "lechonan")
    user = db.query(User).filter_by(username="lechonan").one()
    tokens = sign_in(client, SHOP, "lechonan", BASIC_PASSWORD).json()
    shop = membership(db, user.id, "shop")
    assert shop.status == ACTIVE and shop.activated_at and shop.last_login_at
    assert claims(tokens)["aud"] == ["shop", "genesis-api"]
    assert claims(tokens)["svc"] == "shop"


def test_tokens_are_not_interchangeable_between_services(client, services, make_user):
    tokens = sign_in(client, SHOP, make_user().username).json()
    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(tokens["access_token"], options={"verify_signature": False, "verify_aud": True},
                   audience="kitchen")


def test_role_is_per_service(client, db, services, make_user):
    user = make_user()
    member(db, user, "kitchen", role="admin")
    kitchen = sign_in(client, KITCHEN, user.username).json()
    shop = sign_in(client, SHOP, user.username).json()
    assert claims(kitchen)["role"] == "admin"
    assert claims(shop)["role"] == "user"
    me = client.get("/users/me/", headers=bearer(kitchen)).json()
    assert (me["role"], me["service"], me["membership_status"]) == ("admin", "kitchen", ACTIVE)
    assert client.get("/users/me/", headers=bearer(shop)).json()["role"] == "user"


def test_refresh_keeps_the_service(client, services, make_user):
    tokens = sign_in(client, KITCHEN, make_user().username).json()
    refreshed = client.post("/refresh_token", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert refreshed.status_code == 200
    assert claims(refreshed.json())["svc"] == "kitchen"


def test_root_works_on_every_service_without_memberships(client, db, services, make_user):
    root = make_user(role="root")
    tokens = sign_in(client, KITCHEN, root.username).json()
    assert claims(tokens)["role"] == "root"
    assert client.get("/users/me/", headers=bearer(tokens)).json()["role"] == "root"
    assert db.query(ServiceMembership).filter_by(user_id=root.id).count() == 0


def test_tokens_from_before_services_follow_their_session(client, db, services, make_user, login):
    user = make_user()
    tokens = login(user)  # Genesis context: no "svc" claim, like a pre-0.4.0 token
    db.query(LoginSession).filter_by(user_id=user.id).update({"service_id": "shop"})
    db.commit()
    member(db, user, "shop", role="admin")
    me = client.get("/users/me/", headers=bearer(tokens)).json()
    assert (me["service"], me["role"]) == ("shop", "admin")


def test_password_change_uses_the_session_service_policy(client, services, make_user):
    user = make_user()
    kitchen = sign_in(client, KITCHEN, user.username).json()
    changed = client.post("/users/me/password", headers=bearer(kitchen),
                          json={"current_password": PASSWORD, "new_password": BASIC_PASSWORD})
    assert changed.status_code == 200, changed.text
    shop = sign_in(client, SHOP, user.username, BASIC_PASSWORD).json()
    weak = client.post("/users/me/password", headers=bearer(shop),
                       json={"current_password": BASIC_PASSWORD, "new_password": "kusina99"})
    assert weak.status_code == 422


# ---- a service's administrators ------------------------------------------------------

@pytest.fixture
def kitchen_admin(client, db, services, make_user):
    admin = make_user()
    member(db, admin, "kitchen", role="admin")
    return bearer(sign_in(client, KITCHEN, admin.username).json())


def test_service_admin_sees_only_its_members(client, db, kitchen_admin, make_user):
    customer, shop_only = make_user(), make_user()
    member(db, customer, "kitchen")
    member(db, shop_only, "shop")
    sync_services(db)  # shop_only is now pending on the kitchen
    names = {u["username"] for u in client.get("/admin/users", headers=kitchen_admin).json()["users"]}
    assert customer.username in names and shop_only.username not in names
    assert client.get(f"/admin/users/{shop_only.id}", headers=kitchen_admin).status_code == 404
    detail = client.get(f"/admin/users/{customer.id}", headers=kitchen_admin).json()
    assert detail["membership_status"] == ACTIVE and detail["memberships"] == []


def test_suspension_is_per_service(client, db, kitchen_admin, make_user):
    user = make_user()
    member(db, user, "kitchen")
    kitchen = sign_in(client, KITCHEN, user.username).json()
    response = client.post(f"/admin/users/{user.id}/disable", headers=kitchen_admin)
    assert response.json() == {"message": "User disabled", "disabled": True}
    assert membership(db, user.id, "kitchen").status == SUSPENDED
    assert client.get("/users/me/", headers=bearer(kitchen)).status_code in (401, 403)
    refreshed = client.post("/refresh_token", headers={"Authorization": f"Bearer {kitchen['refresh_token']}"})
    assert refreshed.status_code in (401, 403)
    assert sign_in(client, KITCHEN, user.username).status_code == 403
    shop = sign_in(client, SHOP, user.username)
    assert shop.status_code == 200
    assert client.get("/users/me/", headers=bearer(shop.json())).status_code == 200
    assert client.post(f"/admin/users/{user.id}/disable", headers=kitchen_admin).json()["disabled"] is False


def test_only_root_grants_admin_and_only_on_that_service(client, db, kitchen_admin, make_user):
    user = make_user()
    member(db, user, "kitchen")
    assert client.post(f"/admin/users/{user.id}/role", json={"role": "admin"}, headers=kitchen_admin).status_code == 403
    root = bearer(sign_in(client, KITCHEN, make_user(role="root").username).json())
    assert client.post(f"/admin/users/{user.id}/role", json={"role": "admin"}, headers=root).status_code == 200
    assert membership(db, user.id, "kitchen").role == "admin"
    db.expire_all()
    assert db.get(User, user.id).role == "user"
    assert claims(sign_in(client, SHOP, user.username).json())["role"] == "user"


def test_genesis_wide_actions_are_refused_to_service_admins(client, db, kitchen_admin, make_user):
    user = make_user()
    member(db, user, "kitchen")
    assert client.delete(f"/admin/users/{user.id}", headers=kitchen_admin).status_code == 403
    assert client.post(f"/admin/users/{user.id}/password", json={"generate": True}, headers=kitchen_admin).status_code == 403
    for path in ("/admin/analytics", "/admin/requests", "/admin/clients", "/users/"):
        assert client.get(path, headers=kitchen_admin).status_code == 403
    assert client.get(f"/users/{user.id}", headers=kitchen_admin).status_code == 403


def test_genesis_admin_list_shows_the_source(client, db, services, make_user, login):
    register(client, KITCHEN, "bakeshop")
    root = make_user(role="root")
    rows = client.get("/admin/users?source=kitchen", headers=bearer(login(root))).json()["users"]
    assert [(r["username"], r["registered_via"]) for r in rows] == [("bakeshop", "kitchen")]
    user = db.query(User).filter_by(username="bakeshop").one()
    detail = client.get(f"/admin/users/{user.id}", headers=bearer(login(root))).json()
    assert {m["service"]: m["status"] for m in detail["memberships"]} == {"kitchen": ACTIVE, "shop": PENDING}


def test_service_admin_creates_members_of_its_own_service(client, db, kitchen_admin):
    response = client.post("/admin/users", headers=kitchen_admin,
                           json={"username": "walkin", "email": "walkin@example.com"})
    assert response.status_code == 201, response.text
    user = db.query(User).filter_by(username="walkin").one()
    assert (user.role, user.registered_via) == ("user", "kitchen")
    assert membership(db, user.id, "kitchen").joined_via == "admin"
    assert membership(db, user.id, "shop").status == PENDING
