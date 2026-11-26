#!/bin/bash
set -e #Persist if a command fails, keep running the script

# Run from the project root
cd "$(dirname "$0")/.."

echo "Starting Vault..."
docker compose up -d vault

# Fix permissions on the persistent volume
echo "Checking Vault data permissions..."
docker compose run --rm --user root --entrypoint sh vault \
    -c "chown -R 100:1000 /vault/data"

# Wait until Vault responds
echo "Waiting for Vault..."
while true; do
    STATUS=$(docker compose exec -T vault vault status 2>&1 || true)

    if echo "$STATUS" | grep -q "Initialized"; then
        break
    fi

    sleep 2
done

# Initialize only on the first run
if echo "$STATUS" | grep -q "Initialized.*false"; then
    echo "Vault has not been initialized. Initializing..."
    docker compose exec vault vault operator init

    echo "IMPORTANT: Save your unseal keys and root token securely."
    exit 0
fi

# Handle sealed Vault
if echo "$STATUS" | grep -q "Sealed.*true"; then
    echo "Vault is initialized but sealed."
    echo "Run the unseal command three times with different keys:"
    echo "docker compose exec vault vault operator unseal"
    exit 0
fi

echo "Vault is ready at http://127.0.0.1:18201"
