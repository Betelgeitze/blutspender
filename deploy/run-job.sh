#!/usr/bin/env bash
# Cron wrapper for the one-shot services (parser, sender) and for backup.sh.
# Timestamps output, keeps a per-job log, and — if ADMIN_CHAT_ID is set in .env —
# sends a Telegram message when a job fails.
#
#   ./deploy/run-job.sh parser
#   ./deploy/run-job.sh sender
#   ./deploy/run-job.sh backup
#
# On ECS you had CloudWatch. Here nothing watches these jobs, so a parser that
# starts failing is invisible until users notice missing appointments. Set
# ADMIN_CHAT_ID to your own Telegram chat id to get told instead.
set -Eeuo pipefail

JOB="${1:-}"
if [ -z "$JOB" ]; then
    echo "usage: $0 <parser|sender|backup>" >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/deploy/logs"
cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR"

set -a; . ./.env; set +a
LOG="${LOG_DIR}/${JOB}.log"

notify_failure() {
    local code="$1"
    echo "[$(date -Is)] ${JOB} FAILED (exit ${code})" | tee -a "$LOG"
    if [ -n "${ADMIN_CHAT_ID:-}" ] && [ -n "${BOT_API_KEY:-}" ]; then
        curl -sS -m 15 -o /dev/null \
            --data-urlencode "chat_id=${ADMIN_CHAT_ID}" \
            --data-urlencode "text=blutspender: ${JOB} failed (exit ${code}) on $(hostname). Last lines:
$(tail -n 15 "$LOG")" \
            "https://api.telegram.org/bot${BOT_API_KEY}/sendMessage" || true
    fi
}

echo "[$(date -Is)] ${JOB} starting" >> "$LOG"

case "$JOB" in
    parser|sender)
        # --rm so the container is discarded; the "jobs" profile keeps these out
        # of "docker compose up".
        docker compose run --rm "$JOB" >> "$LOG" 2>&1 || { notify_failure $?; exit 1; }
        ;;
    backup)
        "${PROJECT_DIR}/deploy/backup.sh" >> "$LOG" 2>&1 || { notify_failure $?; exit 1; }
        ;;
    *)
        echo "unknown job: ${JOB}" >&2
        exit 1
        ;;
esac

echo "[$(date -Is)] ${JOB} ok" >> "$LOG"

# Keep logs from growing without bound on a 40GB disk.
for f in "$LOG_DIR"/*.log; do
    [ -f "$f" ] || continue
    if [ "$(stat -c %s "$f")" -gt 5000000 ]; then
        tail -c 1000000 "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
    fi
done
