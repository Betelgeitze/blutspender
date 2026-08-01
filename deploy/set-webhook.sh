#!/usr/bin/env bash
# Register, inspect, or remove the Telegram webhook by hand.
#
#   bash deploy/set-webhook.sh           register WEBHOOK_DOMAIN, keep queued updates
#   bash deploy/set-webhook.sh --drop    same, but discard the backlog (cutover only)
#   bash deploy/set-webhook.sh --status  what Telegram currently thinks
#   bash deploy/set-webhook.sh --delete  remove it, so polling can take over
#
# The bot registers itself on every start, so you rarely need this. It exists for
# the two cases where that is not enough: diagnosing why updates stopped
# (--status shows Telegram's own last_error_message, which is the single most
# useful line when a webhook goes quiet), and switching back to polling.
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
set -a; . ./.env; set +a

: "${BOT_API_KEY:?BOT_API_KEY is not set in .env}"
API="https://api.telegram.org/bot${BOT_API_KEY}"

case "${1:-}" in
    --status)
        curl -sS "${API}/getWebhookInfo"
        echo
        exit 0
        ;;
    --delete)
        # drop_pending_updates=false: whatever queued up is still real user
        # traffic, and polling will pick it up.
        curl -sS "${API}/deleteWebhook?drop_pending_updates=false"
        echo
        echo "Webhook removed. Set BOT_MODE=polling and clear COMPOSE_PROFILES in"
        echo ".env, then: docker compose up -d bot"
        exit 0
        ;;
    --drop) DROP=true ;;
    "")     DROP=false ;;
    *)
        echo "usage: $0 [--drop|--status|--delete]" >&2
        exit 1
        ;;
esac

: "${WEBHOOK_DOMAIN:?WEBHOOK_DOMAIN is not set in .env}"
: "${WEBHOOK_SECRET:?WEBHOOK_SECRET is not set in .env}"

# Must match WEBHOOK_PATH in bot/webhook.py.
URL="https://${WEBHOOK_DOMAIN}/telegram-webhook"

echo "Registering ${URL} (drop_pending_updates=${DROP})"
curl -sS -X POST "${API}/setWebhook" \
    --data-urlencode "url=${URL}" \
    --data-urlencode "secret_token=${WEBHOOK_SECRET}" \
    --data-urlencode "drop_pending_updates=${DROP}" \
    --data-urlencode "max_connections=20"
echo
echo
echo "Now:"
curl -sS "${API}/getWebhookInfo"
echo
echo
echo 'Healthy looks like: "pending_update_count":0 and no "last_error_message".'
echo 'A last_error_message about certificates means Caddy has not finished'
echo 'issuing yet — check: docker compose logs caddy'
