import pytest
import requests

BASE_URL = "http://localhost:8000"  # Change to your actual server URL

def make_request(method, endpoint, **kwargs):
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

@pytest.fixture
def user_data():
    return {
        "username": "dev",
        "email": "test@dev.com",
        "password": "HelloWorld@123"
    }

@pytest.fixture
def tokens(user_data):
    # Create user or handle existing user
    response = make_request("post", "/users/", json=user_data)
    if response.status_code == 200:
        print("[+] User created successfully.")
    elif response.status_code == 400:
        print("[+] User already exists, continuing with authentication...")
    else:
        pytest.fail(f"Unexpected response while creating user: {response.status_code}")

    # Authenticate and get tokens
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = make_request("post", "/token", data=auth_data)
    assert response.status_code == 200, f"Authentication failed: {response.status_code}"
    
    token = response.json().get("access_token")
    refresh_token = response.json().get("refresh_token")
    
    assert token, "[!] Failed to retrieve access token."
    assert refresh_token, "[!] Failed to retrieve refresh token."

    return token, refresh_token

def test_check_me(tokens):
    token, _ = tokens
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("get", "/users/me/", headers=headers)
    assert response.status_code == 200, f"Failed to retrieve user data: {response.status_code}"
    print("[+] Successfully retrieved user data.")

def test_refresh_token(tokens):
    _, refresh_token = tokens
    headers = {"Authorization": f"Bearer {refresh_token}"}
    response = make_request("post", "/refresh_token", headers=headers)
    assert response.status_code == 200, f"Refresh token failed: {response.status_code}"
    
    new_token = response.json().get("access_token")
    new_refresh_token = response.json().get("refresh_token")
    
    assert new_token, "[!] Failed to retrieve new access token."
    assert new_refresh_token, "[!] Failed to retrieve new refresh token."

    return new_token, new_refresh_token

def test_authentication_flow(tokens):
    token, refresh_token = tokens
    
    # Step 2: Check /users/me/ with the initial access token
    test_check_me((token, refresh_token))
    
    # Step 3: Refresh tokens
    new_token, new_refresh_token = test_refresh_token((token, refresh_token))
    
    # Step 4: Check /users/me/ with the new access token
    test_check_me((new_token, new_refresh_token))
    
    print("\n[+] Test sequence completed successfully!")
    print(f"Initial Access Token: {token}")
    print(f"New Access Token: {new_token}")
    print(f"New Refresh Token: {new_refresh_token}")

if __name__ == "__main__":
    pytest.main(["-s", __file__])
