#!/bin/bash
set -e

cd "$(dirname "$0")/.."

SECRETS_FILE="vault/secrets.env"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "Error: $SECRETS_FILE not found."
    exit 1
fi

echo "Checking Vault..."
STATUS=$(docker compose exec -T vault vault status 2>&1 || true)

if echo "$STATUS" | grep -q "Sealed.*true"; then
    echo "Vault is sealed. Unseal it first."
    exit 1
fi

if ! echo "$STATUS" | grep -q "Initialized.*true"; then
    echo "Vault is not initialized."
    exit 1
fi

echo "Loading secrets..."

set -a
source "$SECRETS_FILE"
set +a

: "${DB_PASSWORD:?DB_PASSWORD is missing}"
: "${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is missing}"
: "${DB_USER_PASSWORD:?DB_USER_PASSWORD is missing}"
: "${GOOGLE_CLIENT_SECRET:?GOOGLE_CLIENT_SECRET is missing}"

docker compose exec -T \
    -e DB_PASSWORD="$DB_PASSWORD" \
    -e DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD" \
    -e DB_USER_PASSWORD="$DB_USER_PASSWORD" \
    -e GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
    vault sh -c '
        vault kv put kv/waurd \
            DB_PASSWORD="$DB_PASSWORD" \
            DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD" \
            DB_USER_PASSWORD="$DB_USER_PASSWORD" \
            GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET"
    '

echo "Secrets uploaded successfully to kv/waurd."