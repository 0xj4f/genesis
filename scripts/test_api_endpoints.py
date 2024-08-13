import requests
import pytest
from faker import Faker

# Base URL for the API
BASE_URL = "http://localhost:8000"  # Replace with your actual URL

# Initialize Faker for generating test data
fake = Faker()

# Helper function to generate random user data
def generate_user_data():
    return {
        "username": fake.user_name(),
        "email": fake.email(),
        "password": "SecureP@ssw0rd123"  # Use a fixed password to simplify testing
    }

@pytest.fixture(scope="module")
def create_users():
    user_ids = []
    # Create 5 users
    for _ in range(5):
        user_data = generate_user_data()
        response = requests.post(f"{BASE_URL}/users/", json=user_data)
        assert response.status_code == 200
        user_id = response.json()['id']
        user_ids.append(user_id)
    return user_ids

def test_get_all_users():
    response = requests.get(f"{BASE_URL}/users/")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)

def test_get_users_by_id(create_users):
    user_ids = create_users
    for user_id in user_ids:
        response = requests.get(f"{BASE_URL}/users/{user_id}")
        assert response.status_code == 200
        user = response.json()
        assert user['id'] == str(user_id)

def test_get_users_by_email(create_users):
    user_ids = create_users
    for user_id in user_ids:
        response = requests.get(f"{BASE_URL}/users/{user_id}")
        assert response.status_code == 200
        user = response.json()
        response = requests.post(f"{BASE_URL}/users/search", json={"email": user['email']})
        assert response.status_code == 200
        found_user = response.json()
        assert found_user['email'] == user['email']

def test_get_users_by_username(create_users):
    user_ids = create_users
    for user_id in user_ids:
        response = requests.get(f"{BASE_URL}/users/{user_id}")
        assert response.status_code == 200
        user = response.json()
        response = requests.post(f"{BASE_URL}/users/search", json={"username": user['username']})
        assert response.status_code == 200
        found_user = response.json()
        assert found_user['username'] == user['username']

def test_delete_users(create_users):
    user_ids = create_users
    for user_id in user_ids:
        response = requests.delete(f"{BASE_URL}/users/{user_id}")
        assert response.status_code == 200
        assert response.json()['message'] == f"User with ID {user_id} has been successfully deleted"

        # Verify deletion
        response = requests.get(f"{BASE_URL}/users/{user_id}")
        assert response.status_code == 404
        assert response.json()['detail'] == "User not found"
