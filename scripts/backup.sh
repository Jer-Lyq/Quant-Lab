#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/opt/quant-lab}"
BACKUP_DIR="$APP_DIR/backups"
DATE="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ -f "$APP_DIR/data/quant_lab.sqlite3" ]; then
  cp "$APP_DIR/data/quant_lab.sqlite3" "$BACKUP_DIR/quant_lab_$DATE.sqlite3"
fi

find "$BACKUP_DIR" -name "quant_lab_*.sqlite3" -type f -mtime +7 -delete

