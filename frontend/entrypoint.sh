#!/bin/sh
set -e

cd /frontend_inside_container

if [ ! -x node_modules/.bin/vite ]; then
    echo "Installing dependencies..."
    npm ci
fi

exec "$@"