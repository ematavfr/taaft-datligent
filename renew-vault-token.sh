#!/bin/bash
# renew-project-token.sh

set -euo pipefail

if [ ! -f .vault ]; then
  echo "Error: .vault file not found" >&2
  exit 1
fi

export VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
export VAULT_TOKEN=$(cat .vault)

# Renouveler le token
if vault token renew > /dev/null 2>&1; then
  echo "✅ Token renewed successfully"
  vault token lookup | grep -E "(expire_time|ttl)"
else
  echo "❌ Failed to renew token (may be expired or not renewable)" >&2
  exit 1
fi
