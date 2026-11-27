#!/bin/bash
set -e

cd "$(dirname "$0")/.."

ROLE_NAME="waurd-backend"
CREDENTIALS_FILE="vault/approle.env"

echo "Checking Vault status..."

STATUS=$(docker compose exec -T vault vault status 2>&1 || true)

if echo "$STATUS" | grep -q "Sealed.*true"; then
    echo "Vault is sealed. Please unseal it first."
    exit 1
fi

if ! echo "$STATUS" | grep -q "Initialized.*true"; then
    echo "Vault is not initialized."
    exit 1
fi

if [ -s "$CREDENTIALS_FILE" ]; then
    echo "AppRole credentials already exist."
    echo "Keeping existing credentials."
    exit 0
fi

echo "Retrieving Role ID..."
ROLE_ID=$(docker compose exec -T vault \
    vault read -field=role_id "auth/approle/role/$ROLE_NAME/role-id")

echo "Generating Secret ID..."
SECRET_ID=$(docker compose exec -T vault \
    vault write -field=secret_id -f "auth/approle/role/$ROLE_NAME/secret-id")

echo "Saving credentials locally..."

umask 077
printf 'VAULT_ROLE_ID=%s\nVAULT_SECRET_ID=%s\n' \
    "$ROLE_ID" "$SECRET_ID" > "$CREDENTIALS_FILE"

chmod 600 "$CREDENTIALS_FILE"

echo "AppRole credentials generated successfully!"
echo "Saved in $CREDENTIALS_FILE"