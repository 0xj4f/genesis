#!/bin/sh
set -e
umask 077

# Generate RSA keys if they don't exist
if [ ! -f "${OAUTH_PRIVATE_KEY_PATH:-./secrets/dev-private.pem}" ]; then
    echo "Generating RSA key pair..."
    python -m app.cli generate-keys --output-dir ./secrets
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed ROOT superadmin (Adam) if not exists
echo "Checking seed data..."
python -m app.database.seed

# Start the application
echo "Starting Genesis IAM..."
# Keep one worker, matching the existing single-replica Recreate Helm deployment,
# so all requests share the same in-process limits and single-use SSO state.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-server-header --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
