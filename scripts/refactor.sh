#!/bin/bash

# Function to create the new directory structure
create_structure() {
    echo "Creating new directory structure..."
    mkdir -p app/{models,database,routes,utils,schemas,core}
    mkdir -p tests
    echo "Directory structure created."
}

# Function to move files into their respective directories
move_files() {
    echo "Moving files..."

    # Move models
    mv api_models.py app/models/
    mv database_models.py app/models/
    mv models.py app/models/

    # Move database config and interface
    mv database_config.py app/database/
    mv database_interface.py app/database/

    # Move test scripts to tests directory
    mv scripts/test_auth_flow.py tests/
    mv scripts/test_user_api.py tests/
    mv scripts/raw_test_auth_flow.py tests/

    # Move main FastAPI entry point
    mv main.py app/

    # Move other scripts into utils if necessary
    # Example: mv some_script.py app/utils/

    # Move the remaining SQL scripts into a database folder if desired
    # mv scripts/init.sql app/database/
    # mv scripts/drop-tables.sql app/database/

    echo "Files moved."
}

# Function to update import paths
update_imports() {
    echo "Updating import paths..."

    # Update imports in the moved files
    find app/ -type f -name "*.py" -exec sed -i 's/from api_models/from app.models.api_models/g' {} +
    find app/ -type f -name "*.py" -exec sed -i 's/from database_models/from app.models.database_models/g' {} +
    find app/ -type f -name "*.py" -exec sed -i 's/from models/from app.models.models/g' {} +

    find app/ -type f -name "*.py" -exec sed -i 's/from database_config/from app.database.database_config/g' {} +
    find app/ -type f -name "*.py" -exec sed -i 's/from database_interface/from app.database.database_interface/g' {} +

    echo "Imports updated."
}

# Function to create an example .env file
create_env_file() {
    echo "Creating example .env file..."
    cat > .env <<EOL
SECRET_KEY="your_secret_key"
DATABASE_URL="postgresql://user:password@localhost/dbname"
EOL
    echo ".env file created."
}

# Function to display instructions for running the FastAPI app
display_instructions() {
    echo "Setup complete."
    echo ""
    echo "To run your FastAPI development server:"
    echo "1. Activate your virtual environment (if applicable)."
    echo "2. Run the following command:"
    echo ""
    echo "   uvicorn app.main:app --reload"
    echo ""
    echo "The app will be served on http://127.0.0.1:8000 by default."
    echo ""
    echo "Ensure you have your environment variables set up in the .env file."
}

# Main script execution
create_structure
move_files
update_imports
create_env_file
display_instructions

echo "Project organized successfully!"
