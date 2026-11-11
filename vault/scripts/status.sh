#!/bin/sh

docker compose exec vault sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 && vault status'
