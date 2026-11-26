#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Checking Vault status..."

STATUS=$(docker compose exec -T vault vault status 2>&1 || true)

if echo "$STATUS" | grep -q "Sealed.*true"; then
    echo "Vault is sealed. Please unseal it first."
    exit 1
fi

if ! echo "$STATUS" | grep -q "Initialized.*true"; then
    echo "Vault is not initialized. Run ./vault/start.sh first."
    exit 1
fi

echo "Vault is ready."

echo "Enabling KV v2..."
if ! docker compose exec -T vault vault secrets list | grep -q '^kv/'; then
    docker compose exec vault vault secrets enable -path=kv kv-v2
else
    echo "KV v2 is already enabled."
fi

echo "Installing Waurd policy..."
docker compose exec -T vault vault policy write waurd-policy - < vault/policies/waurd-policy.hcl

echo "Enabling AppRole..."
if ! docker compose exec -T vault vault auth list | grep -q '^approle/'; then
    docker compose exec vault vault auth enable approle
else
    echo "AppRole is already enabled."
fi

echo "Configuring Waurd backend role..."
docker compose exec vault vault write auth/approle/role/waurd-backend \
    token_policies="waurd-policy" \
    token_ttl="1h" \
    token_max_ttl="4h"

echo ""
echo "Vault configuration completed successfully!"
EOF

chmod +x vault/configure.sh