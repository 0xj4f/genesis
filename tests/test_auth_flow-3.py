import pytest
import requests
import jwt

BASE_URL = "http://localhost:8000"
USERNAME = "dev"
PASSWORD = "HelloWorld@123"


@pytest.fixture
def login():
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "",
        "client_id": "string",
        "client_secret": "string",
    }
    response = requests.post(f"{BASE_URL}/token", data=data)
    assert response.status_code == 200, f"Login failed with status code {response.status_code}, Response: {response.text}"
    
    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    
    assert access_token, "Access token is missing in the response."
    assert refresh_token, "Refresh token is missing in the response."
    
    return access_token, refresh_token


def test_validate_token(login):
    access_token, _ = login
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
    }
    response = requests.post(f"{BASE_URL}/token/validate", headers=headers)
    assert response.status_code == 200, f"Token validation failed with status code {response.status_code}, Response: {response.text}"
    data = response.json()
    assert "user_id" in data, "Token validation response missing user_id."
    assert "username" in data, "Token validation response missing username."


def test_forged_token(login):
    access_token, _ = login
    
    # Decode the original token without verifying the signature
    decoded_payload = jwt.decode(access_token, options={"verify_signature": False})
    
    # Modify the payload (forging attempt)
    decoded_payload["username"] = "forged_user"
    
    # Re-encode the token with an incorrect secret
    forged_token = jwt.encode(decoded_payload, "wrong_secret_key", algorithm="HS256")
    
    headers = {
        "Authorization": f"Bearer {forged_token}",
        "accept": "application/json",
    }
    response = requests.post(f"{BASE_URL}/token/validate", headers=headers)
    
    # Expecting token validation failure
    assert response.status_code == 401, f"Forged token validation should fail but passed with status code {response.status_code}. Response: {response.text}"
