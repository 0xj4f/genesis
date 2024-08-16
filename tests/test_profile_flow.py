import pytest
import requests

BASE_URL = "http://localhost:8000"  # Change to your actual server URL

@pytest.fixture(scope="module")
def user_data():
    return {
        "username": "devtest",
        "email": "devtest@dev.com",
        "password": "HelloWorld@123"
    }

@pytest.fixture(scope="module")
def make_request():
    def _make_request(method, endpoint, **kwargs):
        url = f"{BASE_URL}{endpoint}"
        print(f"\n[+] Sending {method.upper()} request to {url}")
        if "json" in kwargs:
            print(f"  Request body: {kwargs['json']}")
        if "headers" in kwargs:
            print(f"  Request headers: {kwargs['headers']}")
        
        response = requests.request(method, url, **kwargs)
        
        print(f"  Status Code: {response.status_code}")
        try:
            print(f"  Response: {response.json()}")
        except ValueError:
            print(f"  Response: {response.text}")
        
        return response
    return _make_request

@pytest.fixture(scope="module")
def create_user(make_request, user_data):
    response = make_request("post", "/users/", json=user_data)
    if response.status_code == 200:
        print("[+] User created successfully.")
        user_data["id"] = response.json().get("id")
    elif response.status_code == 400:
        print("[+] User already exists, continuing with authentication...")
        user_data["id"] = response.json().get("id")  # Assuming the ID is returned when the user exists
    else:
        pytest.fail(f"Unexpected response while creating user: {response.status_code}")
    
    return user_data

@pytest.fixture(scope="module")
def access_token(make_request, create_user):
    auth_data = {
        "username": create_user["username"],
        "password": create_user["password"]
    }
    response = make_request("post", "/token", data=auth_data)
    if response.status_code == 200:
        print("[+] Successful login.")
        token = response.json().get("access_token")
        refresh_token = response.json().get("refresh_token")
        if not token or not refresh_token:
            pytest.fail("Failed to retrieve tokens.")
        return token
    else:
        pytest.fail(f"Authentication failed: {response.status_code}")

def test_create_profile(make_request, access_token, create_user):
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_data = {
        "user_id": create_user["id"],  # Use the actual user ID obtained earlier
        "given_name": "John",
        "family_name": "Doe",
        "nick_name": "Johnny",
        "picture": "http://example.com/picture.jpg",
        "email": "john.doe@example.com",
        "sub": "unique-sub-id"
    }
    response = make_request("post", "/profile/", json=profile_data, headers=headers)
    assert response.status_code == 200, "Profile creation failed."

def test_get_my_profile(make_request, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_request("get", "/profile/me/", headers=headers)
    assert response.status_code == 200, "Failed to retrieve profile."

def test_update_profile(make_request, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_update_data = {
        "given_name": "Jane",
        "family_name": "Smith",
        "nick_name": "Janie",
        "picture": "http://example.com/new-picture.jpg",
        "email": "jane.smith@example.com"
    }
    response = make_request("put", "/profile/me/", json=profile_update_data, headers=headers)
    assert response.status_code == 200, "Profile update failed."

def test_delete_profile(make_request, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_request("delete", "/profile/me/", headers=headers)
    assert response.status_code == 200, "Profile deletion failed."
