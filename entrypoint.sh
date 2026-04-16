#!/bin/sh
set -e

# Generate RSA keys if they don't exist
if [ ! -f "${OAUTH_PRIVATE_KEY_PATH:-./secrets/dev-private.pem}" ]; then
    echo "Generating RSA key pair..."
    python -m app.cli generate-keys --output-dir ./secrets
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting Genesis IAM..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
