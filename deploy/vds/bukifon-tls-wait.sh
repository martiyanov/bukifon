#!/bin/bash
# Ждёт, пока все домены Букифона будут указывать на этот VDS, затем выпускает TLS.
set -u
IP=37.46.18.40
DOMAINS=(bukifon.ru www.bukifon.ru bukifon.com www.bukifon.com)
ok=1
for d in "${DOMAINS[@]}"; do
  a=$(python3 - "$d" <<'PY'
import socket,sys
d=sys.argv[1]
try:
    print(sorted({x[4][0] for x in socket.getaddrinfo(d,443,proto=socket.IPPROTO_TCP)}))
except Exception:
    print("[]")
PY
)
  echo "$(date -Is) $d -> $a"
  case "$a" in *"$IP"*) case "$a" in *92.53.106.182*|*2a03:6f00*) ok=0;; esac;; *) ok=0;; esac
done
if [ "$ok" = "1" ]; then
  echo "$(date -Is) все домены указывают на $IP — выпускаю TLS"
  if certbot --nginx -d bukifon.ru -d www.bukifon.ru -d bukifon.com -d www.bukifon.com --non-interactive --agree-tos --redirect >>/var/log/bukifon-tls.log 2>&1; then
    systemctl reload nginx
    echo "$(date -Is) TLS OK" >>/var/log/bukifon-tls.log
    rm -f /etc/cron.d/bukifon-tls
  fi
else
  echo "$(date -Is) DNS ещё не готов" 
fi
