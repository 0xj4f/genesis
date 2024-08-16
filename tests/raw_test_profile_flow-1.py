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
        "username": "devtest",
        "email": "devtest@dev.com",
        "password": "HelloWorld@123"
    }

    # Create user or handle existing user
    response = make_request("post", "/users/", json=user_data)
    if response.status_code == 200:
        print("[+] User created successfully.")
        user_data["id"] = response.json().get("id")
    elif response.status_code == 400:
        print("[+] User already exists, continuing with authentication...")
        user_data["id"] = response.json().get("id")  # Assuming the ID is returned when the user exists
    else:
        print(f"[!] Unexpected response while creating user: {response.status_code}")
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
            print("[!] Failed to retrieve tokens.")
            return None, None
        return token, refresh_token
    else:
        print(f"[!] Authentication failed: {response.status_code}")
        return None, None

def test_create_profile(token, user_id):
    headers = {"Authorization": f"Bearer {token}"}
    profile_data = {
        "user_id": user_id,  # Use the actual user ID obtained earlier
        "given_name": "John",
        "family_name": "Doe",
        "nick_name": "Johnny",
        "picture": "http://example.com/picture.jpg",
        "email": "john.doe@example.com",
        "sub": "unique-sub-id"
    }
    response = make_request("post", "/profile/", json=profile_data, headers=headers)
    if response.status_code == 200:
        print("[+] Profile created successfully.")
    elif response.status_code == 400:
        print("[!] Profile already exists for this user.")
    return response

def test_get_my_profile(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("get", "/profile/me/", headers=headers)
    if response.status_code == 200:
        print("[+] Successfully retrieved profile.")
    else:
        print("[!] Failed to retrieve profile.")
    return response

def test_update_profile(token):
    headers = {"Authorization": f"Bearer {token}"}
    profile_update_data = {
        "given_name": "Jane",
        "family_name": "Smith",
        "nick_name": "Janie",
        "picture": "http://example.com/new-picture.jpg",
        "email": "jane.smith@example.com"
    }
    response = make_request("put", "/profile/me/", json=profile_update_data, headers=headers)
    if response.status_code == 200:
        print("[+] Profile updated successfully.")
    else:
        print("[!] Failed to update profile.")
    return response

def test_delete_profile(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("delete", "/profile/me/", headers=headers)
    if response.status_code == 200:
        print("[+] Profile deleted successfully.")
    else:
        print("[!] Failed to delete profile.")
    return response

def main():
    print("[*] Starting test sequence...")
    
    # Step 1: Create User
    user_data = test_create_user()
    if not user_data:
        print("[!] Failed to create user or continue with existing user.")
        return

    # Step 2: Get Token
    access_token, _ = test_get_token(user_data)
    if not access_token:
        print("[!] Failed to authenticate and retrieve tokens.")
        return

    # Step 3: Create Profile
    profile_response = test_create_profile(access_token, user_data["id"])
    if profile_response.status_code != 200:
        print("[!] Profile creation failed.")
        return

    # Step 4: Get My Own Profile
    profile_response = test_get_my_profile(access_token)
    if profile_response.status_code != 200:
        print("[!] Failed to retrieve profile.")
        return

    # Step 5: Update Profile
    profile_response = test_update_profile(access_token)
    if profile_response.status_code != 200:
        print("[!] Profile update failed.")
        return

    # Step 6: Delete Profile
    profile_response = test_delete_profile(access_token)
    if profile_response.status_code != 200:
        print("[!] Profile deletion failed.")
        return

    print("\n[+] Test sequence completed successfully!")

if __name__ == "__main__":
    main()
