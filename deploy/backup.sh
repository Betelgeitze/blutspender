#!/usr/bin/env bash
# Nightly Postgres dump with local rotation and optional offsite copy.
#
#   ./deploy/backup.sh
#
# Set RCLONE_REMOTE (e.g. "b2:blutspender-backups") to also push offsite. Local
# dumps alone do not survive losing the VPS — configure the remote.
set -Eeuo pipefail

# Dumps contain chat ids, postcodes and feedback text — personal data. Keep them
# owner-only rather than the default world-readable 0644/0755.
umask 077

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"

cd "$PROJECT_DIR"
set -a; . ./.env; set +a

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"   # umask only covers a dir we create; fix an existing one too
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${BACKUP_DIR}/blutspender-${STAMP}.sql.gz"

# Dump to a .partial name and rename only on success, so an interrupted run
# never leaves a truncated file that looks like a valid backup.
docker compose exec -T database \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
    | gzip -9 > "${DEST}.partial"

mv "${DEST}.partial" "$DEST"

# gzip of an empty/failed dump is ~20 bytes; anything that small is not real data.
SIZE="$(stat -c %s "$DEST")"
if [ "$SIZE" -lt 1000 ]; then
    echo "backup.sh: dump is only ${SIZE} bytes — treating as failed" >&2
    rm -f "$DEST"
    exit 1
fi

echo "backup.sh: wrote ${DEST} (${SIZE} bytes)"

if [ -n "$RCLONE_REMOTE" ]; then
    rclone copy "$DEST" "$RCLONE_REMOTE" --quiet
    echo "backup.sh: copied to ${RCLONE_REMOTE}"
fi

find "$BACKUP_DIR" -name 'blutspender-*.sql.gz' -mtime "+${KEEP_DAYS}" -delete
find "$BACKUP_DIR" -name '*.partial' -mtime +1 -delete
