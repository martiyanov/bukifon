#!/bin/bash
# Ежедневный бэкап сайта Букифона и nginx-конфига. Retention 7.
set -eu
DEST=/var/backups/bukifon
DATE=$(date +%Y%m%d)
mkdir -p "$DEST"
mkdir -p "$DEST/site-$DATE"
rsync -a --delete /var/www/bukifon/ "$DEST/site-$DATE/"
cp /etc/nginx/sites-available/bukifon "$DEST/site-$DATE/nginx-bukifon.conf" 2>/dev/null || true
tar -czf "$DEST/bukifon-$DATE.tar.gz" -C "$DEST" "site-$DATE"
rm -rf "$DEST/site-$DATE"
ls -1t "$DEST"/bukifon-*.tar.gz | tail -n +8 | xargs -r rm -f
echo "$(date -Is) backup ok: $DEST/bukifon-$DATE.tar.gz"
