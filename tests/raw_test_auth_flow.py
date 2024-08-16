# {
#   "username": "dev",
#   "email": "test@dev.com",
#   "password": "HelloWorld!@#"
# }
import requests

BASE_URL = "http://localhost:8000"  # Change to your actual server URL

def test_create_user():
    user_data = {
        "username": "dev",
        "email": "test@dev.com",
        "password": "HelloWorld@123"
    }

    # Create user or handle existing user
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    if response.status_code == 200:
        print("User created successfully.")
    elif response.status_code == 400:
        print("User already exists, continuing with authentication...")
    else:
        print(f"Unexpected response while creating user: {response.status_code}")
        print(response.text)
        return

    # Authenticate and get the token
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/token", data=auth_data)
    if response.status_code == 200:
        print("[+] Successful login.")
    else:
        print(f"Authentication failed: {response.status_code}")
        print(response.text)
        return
    
    token = response.json().get("access_token")
    if not token:
        print("Failed to retrieve access token.")
        return

    # Use the token to authenticate and get the current user
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/users/me/", headers=headers)
    if response.status_code == 200:
        print("Successfully retrieved user data:")
    else:
        print("Failed to retrieve user data:")
    print(response.json())

if __name__ == "__main__":
    test_create_user()
