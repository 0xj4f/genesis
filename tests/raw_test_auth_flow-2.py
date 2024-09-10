import requests
import jwt

BASE_URL = "http://localhost:8000"
USERNAME = "dev"
PASSWORD = "HelloWorld@123"


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
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        print(f"Login successful. Access Token: {access_token}")
        return access_token, refresh_token
    else:
        print(f"Login failed. Status Code: {response.status_code}, Response: {response.text}")
        return None, None


def validate_token(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }
    response = requests.post(f"{BASE_URL}/token/validate", headers=headers)
    if response.status_code == 200:
        print(f"Token validation successful. Response: {response.json()}")
    else:
        print(f"Token validation failed. Status Code: {response.status_code}, Response: {response.text}")


def forge_jwt(token):
    # Decode the original token without verifying the signature
    decoded_payload = jwt.decode(token, options={"verify_signature": False})
    
    # Modify the payload (forging attempt), e.g., change username
    decoded_payload["username"] = "forged_user"
    
    # Re-encode the token with the wrong secret
    forged_token = jwt.encode(decoded_payload, "wrong_secret_key", algorithm="HS256")
    
    print(f"Forged token: {forged_token}")
    return forged_token


def main():
    print("[*] Starting test...")

    # Step 1: Login to get valid tokens
    access_token, _ = login()
    if not access_token:
        return

    # Step 2: Validate the correct token
    print("[*] Validating correct token...")
    validate_token(access_token)

    # Step 3: Forge the token
    forged_token = forge_jwt(access_token)

    # Step 4: Validate the forged token (expect failure)
    print("[*] Validating forged token...")
    validate_token(forged_token)


if __name__ == "__main__":
    main()
