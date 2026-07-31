#!/usr/bin/env bash
# Smoke-test the webhook endpoint without Telegram, TLS, or a domain.
#
#   docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
#   ./deploy/smoke-webhook.sh              checks only
#   ./deploy/smoke-webhook.sh 123456789    also fakes a /start from that chat id
#
# Pass your own Telegram chat id and the bot really does reply to you — that
# covers the whole path except Telegram's delivery: HTTP in, secret check, JSON
# parse, handler dispatch, database, outbound sendMessage.
#
# Runs against 127.0.0.1:8080, which only docker-compose.local.yml publishes.
set -Eeuo pipefail

BASE="http://127.0.0.1:8080"
SECRET="local-test-secret"   # matches docker-compose.local.yml
CHAT_ID="${1:-}"
FAILED=0

check() {
    local name="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  ok    ${name} (${actual})"
    else
        echo "  FAIL  ${name}: expected ${expected}, got ${actual}"
        FAILED=1
    fi
}

code() { curl -sS -o /dev/null -w '%{http_code}' "$@"; }

if ! curl -sS -m 3 -o /dev/null "${BASE}/healthz" 2>/dev/null; then
    echo "Nothing answering on ${BASE}." >&2
    echo "Start it first:" >&2
    echo "  docker compose -f docker-compose.yml -f docker-compose.local.yml up -d" >&2
    exit 1
fi

echo "Testing ${BASE}"

check "healthz" 200 "$(code "${BASE}/healthz")"

# No secret header at all.
check "rejects missing secret" 403 \
    "$(code -X POST -H 'Content-Type: application/json' -d '{}' "${BASE}/telegram-webhook")"

# Wrong secret. This is the check that stands between the bot and anyone who
# guesses the path.
check "rejects wrong secret" 403 \
    "$(code -X POST -H 'Content-Type: application/json' \
        -H 'X-Telegram-Bot-Api-Secret-Token: wrong' -d '{}' "${BASE}/telegram-webhook")"

# Right secret, wrong content type.
check "rejects non-json" 415 \
    "$(code -X POST -H 'Content-Type: text/plain' \
        -H "X-Telegram-Bot-Api-Secret-Token: ${SECRET}" -d 'hello' "${BASE}/telegram-webhook")"

# Unknown path.
check "404s unknown path" 404 "$(code "${BASE}/wp-admin")"

if [ -n "$CHAT_ID" ]; then
    # A minimal but structurally real Update. de_json rejects anything missing
    # the fields telebot dereferences, so this doubles as a parse test.
    read -r -d '' UPDATE <<EOF || true
{"update_id":100000001,
 "message":{"message_id":1,
   "from":{"id":${CHAT_ID},"is_bot":false,"first_name":"Smoke","language_code":"de"},
   "chat":{"id":${CHAT_ID},"first_name":"Smoke","type":"private"},
   "date":1700000000,
   "text":"/start",
   "entities":[{"offset":0,"length":6,"type":"bot_command"}]}}
EOF
    check "accepts a real /start" 200 \
        "$(code -X POST -H 'Content-Type: application/json' \
            -H "X-Telegram-Bot-Api-Secret-Token: ${SECRET}" \
            -d "$UPDATE" "${BASE}/telegram-webhook")"
    echo
    echo "  -> check Telegram: the bot should have sent the welcome message to ${CHAT_ID}."
    echo "     A 200 here only means the update was accepted; handlers run in a"
    echo "     background thread, so failures show in: docker compose logs bot"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo "All checks passed."
else
    echo "Some checks failed — see above." >&2
    exit 1
fi
