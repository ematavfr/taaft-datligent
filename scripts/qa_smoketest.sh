#!/usr/bin/env bash
# TAAFT post-deployment smoke test
# Usage: ./scripts/qa_smoketest.sh [backend_url] [frontend_url]
#   Defaults: http://localhost:8002  http://localhost:3002
set -euo pipefail

BACKEND="${1:-http://localhost:8002}"
FRONTEND="${2:-http://localhost:3002}"
PASS=0
FAIL=0

green() { printf '\033[32m✓\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
red()   { printf '\033[31m✗\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
banner() { printf '\n\033[1m%s\033[0m\n' "$1"; }

http_status() { curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$1"; }
body_contains() { curl -s --max-time 10 "$1" | grep -q "$2"; }

banner "Frontend smoke — $FRONTEND"
status=$(http_status "$FRONTEND" 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
    green "frontend responds 200"
else
    red "frontend responded $status (is the container running?)"
fi

if body_contains "$FRONTEND" "TAAFT" 2>/dev/null; then
    green "HTML contains 'TAAFT'"
else
    red "HTML missing 'TAAFT' text"
fi

banner "Backend quick-check — $BACKEND"
status=$(http_status "$BACKEND/health" 2>/dev/null || echo "000")
if [ "$status" = "200" ]; then
    green "/health → 200"
else
    red "/health → $status (is the backend running?)"
fi

banner "API contract tests"
if command -v python3 &>/dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if python3 "$SCRIPT_DIR/qa_api.py" --url "$BACKEND"; then
        PASS=$((PASS+1))  # count the whole suite as one check here
    else
        FAIL=$((FAIL+1))
    fi
else
    red "python3 not found — skipping API contract tests"
fi

printf '\n%s\n' "──────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
    printf '\033[32m✓ All checks passed\033[0m\n\n'
    exit 0
else
    printf '\033[31m✗ %d check(s) FAILED\033[0m\n\n' "$FAIL"
    exit 1
fi
