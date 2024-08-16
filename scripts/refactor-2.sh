#!/bin/bash

# Create directories if they don't already exist
mkdir -p app/{database,models,routes,services,auth,utils}

# Move files to their respective directories
mv app/models/api_models.py app/models/api_models.py
mv app/models/database_models.py app/models/database_models.py

mv app/database/database_config.py app/database/database_config.py
mv app/database/database_interface.py app/database/database_interface.py

# Creating session management in database
touch app/database/session.py

# Assuming you might have routes and services partially set up, these commands set up their respective directories.
mkdir -p app/routes
mkdir -p app/services

# Initialize profile routes and services if they don't exist
touch app/routes/profiles.py
touch app/routes/users.py
touch app/services/profile_service.py
touch app/services/user_service.py

# Move authentication utilities to auth directory
mv app/utils/auth.py app/auth/auth.py

# Create utility files
touch app/utils/security.py
touch app/utils/helpers.py

echo "Directories and files organized. Please check and manually adjust imports and any missing links in your code."

