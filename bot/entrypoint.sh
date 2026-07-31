#!/bin/sh
# Picks how the bot receives updates. One image, both modes.
#
#   BOT_MODE=webhook   Telegram POSTs to us through Caddy. Default on the VPS.
#   BOT_MODE=polling   We call getUpdates in a loop. No inbound port, no TLS,
#                      no domain — which is what makes it the local-dev and
#                      break-glass mode.
#
# Only one of the two may be active for a given bot token: Telegram answers
# getUpdates with 409 Conflict while a webhook is registered. Switching back to
# polling therefore means deleting the webhook first (see deploy/README.md).
set -e

if [ "${BOT_MODE:-webhook}" = "webhook" ]; then
    echo "Starting webhook mode on :8080..."
    # One worker: webhook.py registers the webhook at import time, and N workers
    # would issue N setWebhook calls. Threads carry the concurrency.
    exec gunicorn \
        --bind 0.0.0.0:8080 \
        --workers 1 \
        --threads 8 \
        --timeout 30 \
        --access-logfile - \
        --error-logfile - \
        webhook:app
fi

echo "Starting polling mode..."
exec python ./main.py
