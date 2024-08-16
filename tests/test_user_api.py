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


# ==================================================================================================================
# ASYNC TEST SCRIPT THAT IS NOT WORKING 
# import httpx
# import pytest
# from uuid import uuid4
# from pydantic import BaseModel, EmailStr, SecretStr
# from typing import Optional
# import re

# # Configuration
# BASE_URL = "http://localhost:8000"  # Change this URL according to your environment

# # Define Pydantic models to match the API requests and responses
# class UserBase(BaseModel):
#     username: str
#     email: EmailStr
#     password: SecretStr

# class UserCreate(UserBase):
#     pass

# class UserUpdate(BaseModel):
#     username: Optional[str] = None
#     email: Optional[EmailStr] = None
#     password: Optional[SecretStr] = None

# class UserSearchRequest(BaseModel):
#     email: Optional[EmailStr] = None
#     username: Optional[str] = None

# class UserDeleteResponse(BaseModel):
#     message: str

# # Test Data
# user_data = [
#     {"username": f"test_user{i}", "email": f"test_user{i}@example.com", "password": "Password123!@aaaaaAAA"}
#     for i in range(5)
# ]

# # Utility functions
# async def create_user(client: httpx.AsyncClient, user: dict):
#     response = await client.post(f"{BASE_URL}/users/", json=user)
#     response.raise_for_status()
#     return response.json()

# async def get_all_users(client: httpx.AsyncClient):
#     response = await client.get(f"{BASE_URL}/users/")
#     response.raise_for_status()
#     return response.json()

# async def get_user_by_id(client: httpx.AsyncClient, user_id: str):
#     response = await client.get(f"{BASE_URL}/users/{user_id}")
#     response.raise_for_status()
#     return response.json()

# async def get_user_by_email(client: httpx.AsyncClient, email: str):
#     response = await client.post(f"{BASE_URL}/users/search", json={"email": email})
#     response.raise_for_status()
#     return response.json()

# async def get_user_by_username(client: httpx.AsyncClient, username: str):
#     response = await client.post(f"{BASE_URL}/users/search", json={"username": username})
#     response.raise_for_status()
#     return response.json()

# async def delete_user(client: httpx.AsyncClient, user_id: str):
#     response = await client.delete(f"{BASE_URL}/users/{user_id}")
#     response.raise_for_status()
#     return response.json()

# # Test Cases
# @pytest.mark.asyncio
# async def test_user_crud():
#     async with httpx.AsyncClient() as client:
#         created_users = []

#         # Create 5 users
#         for data in user_data:
#             user = await create_user(client, data)
#             created_users.append(user['id'])

#         # Get all users
#         users = await get_all_users(client)
#         assert len(users) >= 5  # Verify that users were created

#         # Get users by ID
#         for user_id in created_users:
#             user = await get_user_by_id(client, user_id)
#             assert user['id'] == user_id

#         # Get users by email
#         for data in user_data:
#             user = await get_user_by_email(client, data['email'])
#             assert user['email'] == data['email']

#         # Get users by username
#         for data in user_data:
#             user = await get_user_by_username(client, data['username'])
#             assert user['username'] == data['username']

#         # Delete created users
#         for user_id in created_users:
#             response = await delete_user(client, user_id)
#             assert response['message'] == f"User with ID {user_id} has been successfully deleted"

#         # Verify users are deleted
#         users = await get_all_users(client)
#         assert all(user['id'] not in created_users for user in users)
