FROM nginx:1.29-alpine

RUN apk add --no-cache openssl

COPY templates/default.conf.template /etc/nginx/templates/default.conf.template
COPY 40-generate-cert.sh /docker-entrypoint.d/40-generate-cert.sh

RUN chmod +x /docker-entrypoint.d/40-generate-cert.sh
