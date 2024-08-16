#!/bin/bash

# Define the base directory
BASEDIR=$(dirname $0)

# Create necessary directories
mkdir -p $BASEDIR/app/{database,models,routes,services,auth,utils}

# Move existing files to appropriate locations
mv $BASEDIR/app/main.py $BASEDIR/app/main.py  # Assuming main stays put, adjust if main logic changes
mv $BASEDIR/app/models/api_models.py $BASEDIR/app/models/api_models.py
mv $BASEDIR/app/models/database_models.py $BASEDIR/app/models/database_models.py

# Create new directories for routes and services
mkdir -p $BASEDIR/app/routes
mkdir -p $BASEDIR/app/services

# Assume creation of new files for structured refactoring
touch $BASEDIR/app/routes/user_routes.py
touch $BASEDIR/app/routes/profile_routes.py
touch $BASEDIR/app/services/user_service.py
touch $BASEDIR/app/services/profile_service.py

# Move and rename auth related files
mv $BASEDIR/app/utils/auth.py $BASEDIR/app/auth/auth_utils.py
touch $BASEDIR/app/auth/security.py

# Notify user of manual changes required
echo "Directories and files set up. Please adjust imports and refactor code according to new structure."

