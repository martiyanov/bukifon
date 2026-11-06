# Деплой сайта на VDS (bukifon.ru / bukifon.com)

Сайт собран из `docs/` (RU/EN) и задеплоен на VDS (тот же, что agonarena.ru) по HTTPS.
Веб-приложение и DAW-плагин — бэклог ([docs/86](86-backlog-webapp-plugin.md)).

## 1. Что задеплоено

| Что | Где |
|---|---|
| Сайт RU | `/` (index.html) |
| Сайт EN | `/en/` |
| Демо (RU/EN, `?lang=en`) | `/demo/` |
| Пресскит/ассеты | `/assets/`, `/press/` |
| `sitemap.xml`, `robots.txt`, `llms.txt` | корень |
| Временный HTTPS | `https://bukifon.37-46-18-40.sslip.io/` |

Файлы: `/var/www/bukifon` (root:root, read-only); nginx vhost — `deploy/nginx/bukifon.conf`.

## 2. DNS (у регистратора)

| Тип | Имя | Значение |
|---|---|---|
| A | `@` (bukifon.ru) | **37.46.18.40** |
| A | `www` (bukifon.ru) | **37.46.18.40** |
| A | `@` (bukifon.com) | **37.46.18.40** |
| A | `www` (bukifon.com) | **37.46.18.40** |
| AAAA | — | **удалить старые** (были 2a03:…) |

Без A-записей TLS не выпустить; после DNS — `bash tools/deploy_vds.sh --tls bukifon.ru www.bukifon.ru bukifon.com www.bukifon.com`.

## 3. Деплой/обновление

```bash
export VDS_HOST=openclaw@<ip>       # не коммитить в репо
bash tools/deploy_vds.sh            # сайт (rsync + reload)
bash tools/deploy_vds.sh --nginx    # + vhost
bash tools/deploy_vds.sh --tls bukifon.ru www.bukifon.ru bukifon.com www.bukifon.com
```

Требования: ssh-ключ, sudo на VDS, rsync/certbot/nginx (уже есть).

## 4. TLS

- certbot --nginx, авто-renew (systemd timer); HSTS можно включить после стабилизации DNS;
- временный сертификат — `bukifon.37-46-18-40.sslip.io` (sslip.io), чтобы сайт был доступен до DNS.

## 5. Проверки

```bash
curl -sI https://bukifon.ru/ | head
curl -s -o /dev/null -w '%{http_code}\n' https://bukifon.ru/demo/?lang=en
curl -s https://bukifon.ru/robots.txt
```

Ожидаемо: 200, HTTPS, `/demo/` 200, RU/EN, sitemap/robots на месте.

## 6. Безопасность/эксплуатация

- никаких секретов/ключей в репозитории; `VDS_HOST` — только в окружении;
- сайт статический (root:root read-only), отдача nginx, gzip, кэш статики;
- бэкап: `rsync` сайта и `/etc/nginx/sites-available/bukifon` (в приватный бэкап);
- UFW: 22/80/443; fail2ban — по возможности;
- канонические URL/OG обновляются после стабилизации доменов.

## 7. Откат

```bash
# на VDS
sudo rsync -a /var/backups/bukifon/last/ /var/www/bukifon/
sudo systemctl reload nginx
```
