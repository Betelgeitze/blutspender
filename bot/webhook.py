"""WSGI entrypoint for webhook mode.

Importing `main` is what registers every @bot.message_handler /
@bot.callback_query_handler on the shared TeleBot instance — this module adds
only the HTTP surface that Telegram POSTs updates to. Polling mode never
imports this file; see bot/entrypoint.sh for the switch.

Served by gunicorn with a single worker, because register_webhook() runs at
import time and N workers would mean N redundant setWebhook calls. Concurrency
comes from threads, and from telebot's own handler pool (threaded=True), not
from processes.
"""
import hmac
import os
from time import sleep

import telebot
from flask import Flask, abort, request

from main import bot  # noqa: F401 — the import registers the handlers

# Fixed path. The shared secret rides in the X-Telegram-Bot-Api-Secret-Token
# header instead of the URL, so it never lands in Caddy's access log, in
# `docker compose logs`, or in a screenshot of getWebhookInfo.
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
WEBHOOK_DOMAIN = os.environ["WEBHOOK_DOMAIN"]
WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

app = Flask(__name__)

# A Telegram update is JSON metadata — files arrive as references, never as
# payload — so anything approaching this size is not a real update. Werkzeug
# rejects an oversized body with 413 instead of reading it into memory. Caddy
# caps it too; this is the backstop for anything that bypasses the proxy.
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024


@app.post(WEBHOOK_PATH)
def receive_update():
    # Telegram echoes back the secret passed to set_webhook. Anything without it
    # is not Telegram, so reject before parsing the body.
    #
    # compare_digest, not !=, because a plain string compare returns as soon as
    # two bytes differ and that timing is measurable in principle. Not a
    # realistic attack across the internet against a 256-bit secret, but the
    # constant-time version costs nothing.
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(supplied, WEBHOOK_SECRET):
        abort(403)
    # is_json, not an equality check on content_type: a "; charset=utf-8" suffix
    # would fail the strict form, and a 415 makes Telegram retry the same update
    # forever.
    if not request.is_json:
        abort(415)

    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])

    # Always 200. Telegram retries any non-2xx and will escalate to backing off
    # the whole webhook, so a single bad update must not look like an outage —
    # process_new_updates already isolates handler exceptions.
    return "", 200


@app.get("/healthz")
def healthz():
    return "ok", 200


def register_webhook(retries=6, delay=5):
    """Point Telegram at this container.

    Runs on every start so a changed domain or secret takes effect on redeploy.
    Retried because two things can legitimately be unready at boot: an old
    polling container may still hold a getUpdates connection (409), and Caddy
    may not have finished the ACME handshake for a brand-new domain.

    drop_pending_updates is deliberately False — on a restart the queue holds
    real user messages from the downtime window. Use deploy/set-webhook.sh
    --drop for the one-time cutover from polling.
    """
    for attempt in range(1, retries + 1):
        try:
            bot.set_webhook(
                url=WEBHOOK_URL,
                secret_token=WEBHOOK_SECRET,
                drop_pending_updates=False,
                max_connections=20,
            )
            print(f"Webhook registered: {WEBHOOK_URL}")
            return
        except Exception as e:
            print(f"set_webhook attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                sleep(delay)

    # Keep serving. The HTTP side is fine; only the registration failed, and
    # set-webhook.sh fixes that without a redeploy.
    print(
        "WEBHOOK NOT REGISTERED after all retries. The bot will receive nothing "
        "until you run ./deploy/set-webhook.sh — check that the certificate has "
        "been issued (docker compose logs caddy)."
    )


register_webhook()
