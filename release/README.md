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

Si es vol fer servir un fqdn i certificats, es pot copiar `.env.docker.example` a `.env.docker` i editar-lo.
Es pot ajustar el SERVER-NAME  i els certificats.

Si no es fa, el sistema generarà automàticament un certificat autosignat i la connexió es farà a la IP del sistema
(https://IP:8499)

## Càrrega de la imatge

```bash
Descarregar fortiACL.tar.gz (wget https://raw.githubusercontent.com/oriollorenzo/FortiACL/main/release/fortiACL.tar.gz)
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
https://<fqdn>:8499 (si no hem definit SERVER_NAME, utilitzar la IP del sistema https://[IP]:8499
```

## Primera instal·lació

- la web redirigeix a `/setup`
- es crea el primer usuari local
- un cop creat, `/setup` deixa d'estar disponible, es només per la creacio del primer administrador

## Notes

- No s'exposa cap port HTTP, només `8499` amb HTTPS.
