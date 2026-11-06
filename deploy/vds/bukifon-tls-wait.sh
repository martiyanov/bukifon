#!/bin/bash
# Ждёт «чистый» DNS для bukifon.com/.ru, затем выпускает TLS. Cron каждые 5 мин.
set -u
IP=37.46.18.40
FORBIDDEN='92.53.106.182|2a03:6f00'
LOG=/var/log/bukifon-tls.log
say(){ echo "$(date -Is) $*" >>"$LOG"; echo "$(date -Is) $*"; }

dns_get(){ # $1=name $2=type -> newline list
  python3 - "$1" "$2" <<'PY'
import json,sys,urllib.request
n,t=sys.argv[1],sys.argv[2]
try:
    with urllib.request.urlopen(f"https://dns.google/resolve?name={n}&type={t}",timeout=10) as r:
        d=json.load(r)
    for a in d.get("Answer",[]):
        if a.get("type")==(1 if t=="A" else 28): print(a["data"])
except Exception as e:
    pass
PY
}
clean(){ # name: A содержит IP, нет запрещённых, AAAA пуст
  local n=$1 a aaaa
  a=$(dns_get "$n" A | tr '\n' ' ')
  aaaa=$(dns_get "$n" AAAA | tr '\n' ' ')
  if echo "$a $aaaa" | grep -Eq "$FORBIDDEN"; then
    say "$n: A=[$a] AAAA=[$aaaa] -> старые IP"; return 1
  fi
  case "$a" in *"$IP"*) ;; *) say "$n: A=[$a] -> нет $IP"; return 1;; esac
  if [ -n "$aaaa" ]; then say "$n: AAAA=[$aaaa] -> удалить AAAA"; return 1; fi
  say "$n: A=[$a] -> ok"; return 0
}
com_ok=0; ru_ok=0
clean bukifon.com && clean www.bukifon.com && com_ok=1
clean bukifon.ru && clean www.bukifon.ru && ru_ok=1

if [ "$com_ok" = "1" ]; then
  if [ ! -f /etc/letsencrypt/live/bukifon.com/cert.pem ]; then
    say "выпускаю TLS bukifon.com+www"
    certbot --nginx -d bukifon.com -d www.bukifon.com --cert-name bukifon.com --non-interactive --agree-tos --redirect >>"$LOG" 2>&1 && systemctl reload nginx
  elif ! certbot certificates 2>/dev/null | grep -A2 "Certificate Name: bukifon.com" | grep -q "www.bukifon.com"; then
    say "расширяю cert bukifon.com на www"
    certbot --nginx -d bukifon.com -d www.bukifon.com --cert-name bukifon.com --expand --non-interactive --agree-tos --redirect >>"$LOG" 2>&1 && systemctl reload nginx
  fi
fi
if [ "$ru_ok" = "1" ] && [ ! -f /etc/letsencrypt/live/bukifon.ru/cert.pem ]; then
  say "выпускаю TLS bukifon.ru+www"
  certbot --nginx -d bukifon.ru -d www.bukifon.ru --cert-name bukifon.ru --non-interactive --agree-tos --redirect >>"$LOG" 2>&1 && systemctl reload nginx
fi

have_com=$(certbot certificates 2>/dev/null | grep -A2 "Certificate Name: bukifon.com" | grep -c "www.bukifon.com" || true)
have_ru=$(certbot certificates 2>/dev/null | grep -A2 "Certificate Name: bukifon.ru" | grep -c "www.bukifon.ru" || true)
if [ "$have_com" = "1" ] && [ "$have_ru" = "1" ]; then
  say "все сертификаты на месте — снимаю cron"
  rm -f /etc/cron.d/bukifon-tls
fi
