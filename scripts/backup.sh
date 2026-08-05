#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/opt/quant-lab}"
BACKUP_DIR="$APP_DIR/backups"
DATE="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ -d "$APP_DIR/data" ]; then
  tar -czf "$BACKUP_DIR/quant_lab_data_$DATE.tar.gz" -C "$APP_DIR" data
fi

find "$BACKUP_DIR" -name "quant_lab_data_*.tar.gz" -type f -mtime +7 -delete
