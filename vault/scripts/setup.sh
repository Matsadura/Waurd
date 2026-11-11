#!/bin/sh

set -e #stops execution if a command fails.

echo "Checking Vault status..."

docker compose exec vault sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 && vault status' #-c execute a command

echo "Vault is ready for configuration."
