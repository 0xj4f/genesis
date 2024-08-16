# # {
# #   "username": "dev",
# #   "email": "test@dev.com",
# #   "password": "HelloWorld!@#"
# # }
# import requests

# BASE_URL = "http://localhost:8000"  # Change to your actual server URL

# def test_create_user():
#     user_data = {
#         "username": "dev",
#         "email": "test@dev.com",
#         "password": "HelloWorld@123"
#     }

#     # Create user or handle existing user
#     response = requests.post(f"{BASE_URL}/users/", json=user_data)
#     if response.status_code == 200:
#         print("User created successfully.")
#     elif response.status_code == 400:
#         print("User already exists, continuing with authentication...")
#     else:
#         print(f"Unexpected response while creating user: {response.status_code}")
#         print(response.text)
#         return

#     # Authenticate and get the token
#     auth_data = {
#         "username": user_data["username"],
#         "password": user_data["password"]
#     }
#     response = requests.post(f"{BASE_URL}/token", data=auth_data)
#     if response.status_code == 200:
#         print("[+] Successful login.")
#     else:
#         print(f"Authentication failed: {response.status_code}")
#         print(response.text)
#         return
    
#     token = response.json().get("access_token")
#     if not token:
#         print("Failed to retrieve access token.")
#         return

#     # Use the token to authenticate and get the current user
#     headers = {"Authorization": f"Bearer {token}"}
#     response = requests.get(f"{BASE_URL}/users/me/", headers=headers)
#     if response.status_code == 200:
#         print("Successfully retrieved user data:")
#     else:
#         print("Failed to retrieve user data:")
#     print(response.json())

# if __name__ == "__main__":
#     test_create_user()

# import requests

# BASE_URL = "http://localhost:8000"  # Change to your actual server URL

# def make_request(method, endpoint, **kwargs):
#     url = f"{BASE_URL}{endpoint}"
#     print(f"[Request] {method.upper()} {url}")
#     if 'json' in kwargs:
#         print("Payload:", kwargs['json'])
#     if 'headers' in kwargs:
#         print("Headers:", kwargs['headers'])

#     response = requests.request(method, url, **kwargs)
#     print(f"[Response] Status Code: {response.status_code}")
#     print("Response Body:", response.json(), "\n")
#     return response

# def create_user(user_data):
#     response = make_request("post", "/users/", json=user_data)
#     if response.status_code == 200:
#         print("User created successfully.")
#     elif response.status_code == 400:
#         print("User already exists, continuing with authentication...")
#     else:
#         print(f"Unexpected response while creating user: {response.status_code}")
#         print(response.text)
#     return response

# def get_token(auth_data):
#     response = make_request("post", "/token", data=auth_data)
#     if response.status_code == 200:
#         print("[+] Successful login.")
#     else:
#         print(f"Authentication failed: {response.status_code}")
#         print(response.text)
#     return response

# def get_refresh_token(refresh_token):
#     headers = {"Authorization": f"Bearer {refresh_token}"}
#     response = make_request("post", "/refresh_token", headers=headers)
#     if response.status_code == 200:
#         print("[+] Successful token refresh.")
#     else:
#         print(f"Token refresh failed: {response.status_code}")
#         print(response.text)
#     return response

# def get_current_user(access_token):
#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = make_request("get", "/users/me/", headers=headers)
#     if response.status_code == 200:
#         print("Successfully retrieved user data.")
#     else:
#         print("Failed to retrieve user data.")
#     return response

# def test_user_flow():
#     user_data = {
#         "username": "dev",
#         "email": "test@dev.com",
#         "password": "HelloWorld@123"
#     }
    
#     # Create user or handle existing user
#     create_user_response = create_user(user_data)
    
#     # Authenticate and get the token
#     auth_data = {
#         "username": user_data["username"],
#         "password": user_data["password"]
#     }
#     token_response = get_token(auth_data)
#     access_token = token_response.json().get("access_token")
#     refresh_token = token_response.json().get("refresh_token")

#     if not access_token or not refresh_token:
#         print("Failed to retrieve tokens.")
#         return
    
#     # Get current user with access token
#     get_current_user(access_token)
    
#     # Refresh the token
#     get_refresh_token(refresh_token)

# if __name__ == "__main__":
#     test_user_flow()
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

def test_create_user():
    user_data = {
        "username": "dev",
        "email": "test@dev.com",
        "password": "HelloWorld@123"
    }

    # Create user or handle existing user
    response = make_request("post", "/users/", json=user_data)
    if response.status_code == 200:
        print("User created successfully.")
    elif response.status_code == 400:
        print("User already exists, continuing with authentication...")
    else:
        print(f"Unexpected response while creating user: {response.status_code}")
        return None

    return user_data

def test_get_token(user_data):
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = make_request("post", "/token", data=auth_data)
    if response.status_code == 200:
        print("[+] Successful login.")
        token = response.json().get("access_token")
        refresh_token = response.json().get("refresh_token")
        if not token or not refresh_token:
            print("Failed to retrieve tokens.")
            return None, None
        return token, refresh_token
    else:
        print(f"Authentication failed: {response.status_code}")
        return None, None

def test_refresh_token(refresh_token):
    headers = {"Authorization": f"Bearer {refresh_token}"}
    response = make_request("post", "/refresh_token", headers=headers)
    if response.status_code == 200:
        print("[+] Successfully refreshed tokens.")
        new_token = response.json().get("access_token")
        new_refresh_token = response.json().get("refresh_token")
        return new_token, new_refresh_token
    else:
        print(f"Refresh token failed: {response.status_code}")
        return None, None

def main():
    print("[*] Starting test sequence...")
    user_data = test_create_user()
    if not user_data:
        print("[!] Failed to create user or continue with existing user.")
        return

    access_token, refresh_token = test_get_token(user_data)
    if not access_token or not refresh_token:
        print("[!] Failed to authenticate and retrieve tokens.")
        return

    new_access_token, new_refresh_token = test_refresh_token(refresh_token)
    if not new_access_token or not new_refresh_token:
        print("[!] Failed to refresh tokens.")
        return

    print("\n[+] Test sequence completed successfully!")
    print(f"Initial Access Token: {access_token}")
    print(f"New Access Token: {new_access_token}")
    print(f"New Refresh Token: {new_refresh_token}")

if __name__ == "__main__":
    main()
