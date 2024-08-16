# import requests

# BASE_URL = "http://localhost:8000"  # Change to your actual server URL

# def make_request(method, endpoint, **kwargs):
#     url = f"{BASE_URL}{endpoint}"
#     print(f"\n[+] Sending {method.upper()} request to {url}")
#     if "json" in kwargs:
#         print(f"  Request body: {kwargs['json']}")
#     if "headers" in kwargs:
#         print(f"  Request headers: {kwargs['headers']}")
    
#     response = requests.request(method, url, **kwargs)
    
#     print(f"  Status Code: {response.status_code}")
#     try:
#         print(f"  Response: {response.json()}")
#     except ValueError:
#         print(f"  Response: {response.text}")
    
#     return response

# def test_create_user():
#     user_data = {
#         "username": "dev",
#         "email": "test@dev.com",
#         "password": "HelloWorld@123"
#     }

#     # Create user or handle existing user
#     response = make_request("post", "/users/", json=user_data)
#     if response.status_code == 200:
#         print("[+] User created successfully.")
#     elif response.status_code == 400:
#         print("[+] User already exists, continuing with profile creation...")
#     else:
#         print(f"[!] Unexpected response while creating user: {response.status_code}")
#         return None

#     return user_data

# def test_create_profile(user_data):
#     profile_data = {
#         "user_id": user_data["id"],
#         "given_name": "John",
#         "family_name": "Doe",
#         "nick_name": "Johnny",
#         "picture": "http://example.com/pic.jpg",
#         "email": user_data["email"],
#         "sub": "sub-example"
#     }

#     response = make_request("post", "/profile/", json=profile_data)
#     if response.status_code == 200:
#         print("[+] Profile created successfully.")
#     else:
#         print(f"[!] Unexpected response while creating profile: {response.status_code}")
#         return None

#     return response.json()

# def test_get_profiles():
#     response = make_request("get", "/profile/")
#     if response.status_code == 200:
#         print("[+] Successfully retrieved profiles.")
#     else:
#         print("[!] Failed to retrieve profiles.")
#     return response.json()

# def test_get_profile_by_id(profile_id):
#     response = make_request("get", f"/profile/{profile_id}")
#     if response.status_code == 200:
#         print("[+] Successfully retrieved profile by ID.")
#     else:
#         print("[!] Failed to retrieve profile by ID.")
#     return response.json()

# def test_update_profile(profile_id):
#     update_data = {
#         "given_name": "Jane",
#         "family_name": "Smith",
#         "nick_name": "Janey",
#         "picture": "http://example.com/new-pic.jpg",
#         "email": "new-email@dev.com",
#         "sub": "new-sub-example"
#     }
#     response = make_request("put", f"/profile/{profile_id}", json=update_data)
#     if response.status_code == 200:
#         print("[+] Profile updated successfully.")
#     else:
#         print("[!] Failed to update profile.")
#     return response.json()

# def test_delete_profile(profile_id):
#     response = make_request("delete", f"/profile/{profile_id}")
#     if response.status_code == 200:
#         print("[+] Profile deleted successfully.")
#     else:
#         print("[!] Failed to delete profile.")
#     return response.json()

# def main():
#     print("[*] Starting test sequence...")
#     user_data = test_create_user()
#     if not user_data:
#         print("[!] Failed to create or retrieve user.")
#         return
    
#     # Update the user_data with the user's ID (you would need to get this from your database or mock it)
#     user_data["id"] = "some-uuid-for-testing"

#     profile_data = test_create_profile(user_data)
#     if not profile_data:
#         print("[!] Failed to create profile.")
#         return

#     profile_id = profile_data.get("id")
#     if not profile_id:
#         print("[!] Profile ID not found.")
#         return

#     profiles = test_get_profiles()
#     if not profiles:
#         print("[!] Failed to retrieve profiles.")
#         return

#     profile_by_id = test_get_profile_by_id(profile_id)
#     if not profile_by_id:
#         print("[!] Failed to retrieve profile by ID.")
#         return

#     updated_profile = test_update_profile(profile_id)
#     if not updated_profile:
#         print("[!] Failed to update profile.")
#         return

#     delete_result = test_delete_profile(profile_id)
#     if not delete_result:
#         print("[!] Failed to delete profile.")
#         return

#     print("\n[+] Test sequence completed successfully!")

# if __name__ == "__main__":
#     main()

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
        print("[+] User created successfully.")
        return response.json()  # Return the created user data including ID
    elif response.status_code == 400 and "already registered" in response.text:
        print("[+] User already exists, retrieving user details...")
        return test_get_user_by_username(user_data["username"])  # Retrieve existing user details
    else:
        print(f"[!] Unexpected response while creating user: {response.status_code}")
        return None

def test_get_user_by_username(username):
    response = make_request("post", "/users/search", json={"username": username})
    if response.status_code == 200:
        print("[+] Successfully retrieved existing user.")
        return response.json()
    else:
        print(f"[!] Failed to retrieve user by username: {response.status_code}")
        return None

def test_create_profile(user_data):
    profile_data = {
        "user_id": user_data["id"],
        "given_name": "John",
        "family_name": "Doe",
        "nick_name": "Johnny",
        "picture": "http://example.com/pic.jpg",
        "email": user_data["email"],
        "sub": "sub-example"
    }

    response = make_request("post", "/profile/", json=profile_data)
    if response.status_code == 200:
        print("[+] Profile created successfully.")
    else:
        print(f"[!] Unexpected response while creating profile: {response.status_code}")
        return None

    return response.json()

def test_get_profiles():
    response = make_request("get", "/profile/")
    if response.status_code == 200:
        print("[+] Successfully retrieved profiles.")
    else:
        print("[!] Failed to retrieve profiles.")
    return response.json()

def test_get_profile_by_id(profile_id):
    response = make_request("get", f"/profile/{profile_id}")
    if response.status_code == 200:
        print("[+] Successfully retrieved profile by ID.")
    else:
        print("[!] Failed to retrieve profile by ID.")
    return response.json()

def test_update_profile(profile_id):
    update_data = {
        "given_name": "Jane",
        "family_name": "Smith",
        "nick_name": "Janey",
        "picture": "http://example.com/new-pic.jpg",
        "email": "new-email@dev.com",
        "sub": "new-sub-example"
    }
    response = make_request("put", f"/profile/{profile_id}", json=update_data)
    if response.status_code == 200:
        print("[+] Profile updated successfully.")
    else:
        print("[!] Failed to update profile.")
    return response.json()

def test_delete_profile(profile_id):
    response = make_request("delete", f"/profile/{profile_id}")
    if response.status_code == 200:
        print("[+] Profile deleted successfully.")
    else:
        print("[!] Failed to delete profile.")
    return response.json()

def main():
    print("[*] Starting test sequence...")
    user_data = test_create_user()
    if not user_data:
        print("[!] Failed to create or retrieve user.")
        return
    
    profile_data = test_create_profile(user_data)
    if not profile_data:
        print("[!] Failed to create profile.")
        return

    profile_id = profile_data.get("id")
    if not profile_id:
        print("[!] Profile ID not found.")
        return

    profiles = test_get_profiles()
    if not profiles:
        print("[!] Failed to retrieve profiles.")
        return

    profile_by_id = test_get_profile_by_id(profile_id)
    if not profile_by_id:
        print("[!] Failed to retrieve profile by ID.")
        return

    updated_profile = test_update_profile(profile_id)
    if not updated_profile:
        print("[!] Failed to update profile.")
        return

    delete_result = test_delete_profile(profile_id)
    if not delete_result:
        print("[!] Failed to delete profile.")
        return

    print("\n[+] Test sequence completed successfully!")

if __name__ == "__main__":
    main()

