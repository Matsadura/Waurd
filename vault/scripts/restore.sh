
#!/bin/bash

set -e

VOLUME="${VOLUME:-waurd_vault_data}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP="$SCRIPT_DIR/vault-data.tar.gz"

echo "Checking Vault backup..."

if [ ! -f "$BACKUP" ]; then
    echo "Error: vault-data.tar.gz not found!"
    exit 1
fi

echo "Checking Docker volume..."

if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    echo "Error: Docker volume '$VOLUME' already exists."
    echo "Restore only on a fresh machine with no existing Vault data."
    exit 1
fi

echo "Creating Docker volume..."
docker volume create "$VOLUME" >/dev/null

echo "Restoring Vault data..."

docker run --rm \
    -v "$VOLUME":/destination \
    -v "$SCRIPT_DIR":/backup:ro \
    alpine \
    tar -xzf /backup/vault-data.tar.gz -C /destination

echo "Vault data restored successfully!"
echo "You can now start Vault with: docker compose up -d vault"

