# общие location'ы сайта (подключается в vhost'ах)
gzip on;
gzip_types text/plain text/css application/javascript application/json image/svg+xml;
gzip_min_length 1024;

location = /app/ { return 302 /demo/; }
location /app/ { return 302 /demo/; }

location / { try_files $uri $uri/ =404; }

location ~* \.(jpg|jpeg|png|webp|gif|ico|svg|woff2?)$ {
    expires 7d;
    add_header Cache-Control "public";
    access_log off;
}

add_header X-Content-Type-Options nosniff always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
add_header X-Frame-Options SAMEORIGIN always;
