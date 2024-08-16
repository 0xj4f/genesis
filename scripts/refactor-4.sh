#!/bin/bash

# Navigate to the app directory (modify this path according to your project structure)
cd app

# Rename api_models.py to user_api_model.py
mv models/api_models.py models/user_api_model.py

# Rename database_models.py to user_db_model.py
mv models/database_models.py models/user_db_model.py

# Update import statements in the Python files within the app directory
find . -type f -name '*.py' -exec sed -i 's/api_models/user_api_model/g' {} +
find . -type f -name '*.py' -exec sed -i 's/database_models/user_db_model/g' {} +

echo "Renaming and refactoring done."
