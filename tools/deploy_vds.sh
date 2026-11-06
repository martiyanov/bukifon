#!/usr/bin/env bash
# Деплой статического сайта Букифона на VDS (nginx + TLS через certbot).
# Использование:
#   VDS_HOST=user@host bash tools/deploy_vds.sh            # только сайт (rsync + reload)
#   VDS_HOST=user@host bash tools/deploy_vds.sh --nginx    # + установить/обновить vhost
#   VDS_HOST=user@host bash tools/deploy_vds.sh --tls bukifon.ru www.bukifon.ru bukifon.com www.bukifon.com
# Требуется: ssh-доступ (ключ), sudo на VDS, домены с A-записью на этот VDS.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${VDS_HOST:?задайте VDS_HOST=user@host}"
REMOTE_STAGE="bukifon-site"
SITE="docs"
FILES=(index.html en demo assets press sitemap.xml robots.txt llms.txt)

case "${1:-}" in
  --nginx|--tls|"") ;;
  *) echo "неизвестный аргумент: $1"; exit 2;;
esac

echo "== upload"
ssh "$VDS_HOST" "mkdir -p ~/$REMOTE_STAGE"
for f in "${FILES[@]}"; do
  rsync -az --delete "$SITE/$f" "$VDS_HOST:$REMOTE_STAGE/$(dirname "$f")/" 2>/dev/null || rsync -az "$SITE/$f" "$VDS_HOST:$REMOTE_STAGE/"
done
# аккуратно: каталоги и файлы
rsync -az --delete "$SITE/en" "$SITE/demo" "$SITE/assets" "$SITE/press" "$VDS_HOST:$REMOTE_STAGE/"
rsync -az "$SITE/index.html" "$SITE/sitemap.xml" "$SITE/robots.txt" "$SITE/llms.txt" "$VDS_HOST:$REMOTE_STAGE/"

echo "== install"
ssh "$VDS_HOST" "sudo install -d -m 755 /var/www/bukifon && sudo rsync -a --delete ~/$REMOTE_STAGE/ /var/www/bukifon/ && sudo chown -R root:root /var/www/bukifon && sudo chmod -R a+rX /var/www/bukifon"

if [ "${1:-}" = "--nginx" ] || [ "${1:-}" = "--tls" ]; then
  echo "== nginx vhost"
  scp -q deploy/nginx/bukifon.conf "$VDS_HOST:/tmp/bukifon-nginx.conf"
  ssh "$VDS_HOST" "sudo cp /tmp/bukifon-nginx.conf /etc/nginx/sites-available/bukifon && sudo ln -sf /etc/nginx/sites-available/bukifon /etc/nginx/sites-enabled/bukifon && sudo nginx -t && sudo systemctl reload nginx"
fi

if [ "${1:-}" = "--tls" ]; then
  shift
  DOMAINS=("$@")
  [ ${#DOMAINS[@]} -gt 0 ] || { echo "укажите домены для --tls"; exit 2; }
  args=(); for d in "${DOMAINS[@]}"; do args+=(-d "$d"); done
  echo "== certbot (${DOMAINS[*]})"
  ssh "$VDS_HOST" "sudo certbot --nginx ${args[*]} --non-interactive --agree-tos --redirect"
fi

echo "== check"
for u in "https://bukifon.37-46-18-40.sslip.io/" "https://bukifon.37-46-18-40.sslip.io/demo/"; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$u") $u"
done
echo "готово"
