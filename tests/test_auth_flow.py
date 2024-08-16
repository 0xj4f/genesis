import pytest
import requests

BASE_URL = "http://localhost:8000"  # Change to your actual server URL

@pytest.fixture(scope="module")
def user_data():
    return {
        "username": "dev",
        "email": "test@dev.com",
        "password": "HelloWorld@123"
    }

@pytest.fixture(scope="module")
def token(user_data):
    # First, ensure the user is created
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    if response.status_code == 422:
        raise AssertionError(f"User creation failed with status code 422: {response.json()}")

    # Authenticate and get the token
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/token", data=auth_data)
    if response.status_code != 200:
        raise AssertionError(f"Failed to authenticate. Status code: {response.status_code}, Response: {response.json()}")

    token = response.json().get("access_token")
    return token

def test_create_user(user_data):
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    assert response.status_code in [200, 400], f"Unexpected status code: {response.status_code}"
    if response.status_code == 400:
        assert response.json()["detail"] in ["Email already registered", "Username already taken"], "Unexpected error message"

def test_authenticate_and_get_token(user_data):
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/token", data=auth_data)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    token = response.json().get("access_token")
    assert token is not None, "Failed to retrieve access token"

def test_get_current_user(user_data, token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/users/me/", headers=headers)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    user_info = response.json()
    assert user_info["username"] == user_data["username"], "Username does not match"

@pytest.mark.order(1)
def test_full_flow(user_data, token):
    test_create_user(user_data)
    test_authenticate_and_get_token(user_data)
    test_get_current_user(user_data, token)
