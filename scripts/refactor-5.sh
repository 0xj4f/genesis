#!/bin/bash

# Navigate to the appropriate directory (modify this path according to your project structure)
cd app

# Rename database_interface.py to user_db_interface.py
mv database/database_interface.py database/user_db_interface.py

# Update import statements in the Python files within the app directory
find . -type f -name '*.py' -exec sed -i 's/database_interface/user_db_interface/g' {} +

echo "Renaming of database_interface and refactoring of imports done."
