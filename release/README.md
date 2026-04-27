# Release package

## Contingut

- `docker-compose.yml`
- `.env.docker.example`
- `docker/nginx/templates/default.conf.template`
- `docker/nginx/Dockerfile`
- `docker/nginx/40-generate-cert.sh`
- carpeta `certs/`
- carpeta `config/`
- carpeta `db/`
- carpeta `logs/`

## Preparació

1. opcionalment copia `.env.docker.example` a `.env.docker`
2. si vols, ajusta `SERVER_NAME`

## Càrrega de la imatge

```bash
gzip -d fortiACL.tar.gz
docker load -i fortiACL.tar
```

## Arrencada

Amb `docker-compose` clàssic:

Sense `.env.docker`:

```bash
docker-compose up -d --build
```

Amb `.env.docker`:

```bash
docker-compose --env-file .env.docker up -d --build
```

## Accés

```text
https://<fqdn>:8499
```

## Primera instal·lació

- la web redirigeix a `/setup`
- es crea el primer usuari local
- un cop creat, `/setup` deixa d'estar disponible

## Certificats i configuració

- Si no existeixen certificats a `certs/`, Nginx generarà un certificat autofirmat automàticament.
- Si no existeix `config/config.yaml`, l'aplicació el crearà automàticament amb una plantilla buida.
- Després del primer accés, tota la configuració funcional es pot fer des de la web.

## Notes

- Els logs es guarden a `logs/`.
- No s'exposa cap port HTTP, només `8499` amb HTTPS.
