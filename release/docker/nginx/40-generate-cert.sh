#!/bin/sh
set -eu

CERT_PATH="${TLS_CERT_PATH:-/certs/fullchain.pem}"
KEY_PATH="${TLS_KEY_PATH:-/certs/privkey.pem}"
SERVER_NAME="${SERVER_NAME:-localhost}"

if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
  exit 0
fi

mkdir -p "$(dirname "$CERT_PATH")"
mkdir -p "$(dirname "$KEY_PATH")"

openssl req -x509 -nodes -newkey rsa:2048 \
  -days 3650 \
  -subj "/CN=${SERVER_NAME}" \
  -keyout "$KEY_PATH" \
  -out "$CERT_PATH"
