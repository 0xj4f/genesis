import requests
import uuid

HOST = "http://localhost:8000"


# Function to create a new user
def create_user(username, email, password):
    return requests.post(
        f"{HOST}/create_user/",
        data={"username": username, "email": email, "password": password},
    ).json()


# Function to get all users
def get_all_users():
    return requests.get(f"{HOST}/get_users/").json()


# Function to get a user by ID
def get_user(user_id):
    return requests.get(f"{HOST}/get_user/{user_id}").json()


# Function to delete a user by ID
def delete_user(user_id):
    return requests.delete(f"{HOST}/delete_user/{user_id}").json()


# Step 1: Create 5 users
print("Creating 5 users...")
users = []
for i in range(5):
    user = create_user(
        username=f"user{i}", email=f"user{i}@example.com", password="password123"
    )
    users.append(user)
    print(f"Created user: {user}")

# Step 2: Retrieve all users
print("\nRetrieving all users...")
all_users = get_all_users()
print(f"All Users: {all_users}")

# Step 3: Retrieve one specific user by ID
print("\nRetrieving a specific user by ID...")
user_id = users[2]["id"]  # Assuming we're retrieving the 3rd user created
user = get_user(user_id)
print(f"User retrieved: {user}")

# Step 4: Delete one specific user by ID
print("\nDeleting a specific user by ID...")
deleted_user = delete_user(user_id)
print(f"Deleted user: {deleted_user}")

# Step 5: Verify the user was deleted
print("\nVerifying user deletion...")
try:
    get_user(user_id)
except Exception as e:
    print(f"User with ID {user_id} successfully deleted.")
