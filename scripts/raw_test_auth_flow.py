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

    # Create user
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    
    if response.status_code == 400:
        print("User already exists, continuing with authentication...")
    elif response.status_code == 200:
        print("User created successfully.")
    else:
        print(f"Unexpected response: {response.status_code}")
        return

    # Authenticate and get the token
    auth_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/token", data=auth_data)

    if response.status_code != 200:
        print(f"Authentication failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    if not token:
        print("Failed to retrieve access token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # Use the token to authenticate and get the current user
    response = requests.get(f"{BASE_URL}/users/me/", headers=headers)

    if response.status_code == 200:
        print("Authenticated successfully.")
        print(response.json())  # Print the user details
    else:
        print(f"Failed to authenticate with token: {response.status_code}")


if __name__ == "__main__":
    test_create_user()
