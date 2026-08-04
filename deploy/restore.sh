#!/usr/bin/env bash
# Restore a dump produced by backup.sh. Destructive: --clean in the dump drops
# existing tables before recreating them.
#
#   ./deploy/restore.sh backups/blutspender-20260730-030000.sql.gz
#
# Also the migration path off AWS RDS. --no-owner --no-privileges are required:
# RDS objects are owned by "postgres", which is not a role in our container.
#   pg_dump -h <rds-host> -U <user> -d <db> --clean --if-exists \
#       --no-owner --no-privileges | gzip > aws.sql.gz
#   scp aws.sql.gz <vps>:/srv/blutspender/backups/
#   ./deploy/restore.sh backups/aws.sql.gz
set -Eeuo pipefail

DUMP="${1:-}"
if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
    echo "usage: $0 <dump.sql.gz>" >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
set -a; . ./.env; set +a

read -rp "This overwrites database '${POSTGRES_DB}'. Type the database name to confirm: " CONFIRM
if [ "$CONFIRM" != "$POSTGRES_DB" ]; then
    echo "aborted" >&2
    exit 1
fi

# Stop the bot so it cannot write mid-restore; the database stays up.
docker compose stop bot

gunzip -c "$DUMP" | docker compose exec -T database \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1

docker compose start bot
echo "restore.sh: restored ${DUMP}"
