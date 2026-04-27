# FortiSwitch ACL Manager

Aplicació web per gestionar ACLs `prelookup` en FortiSwitch a partir de la topologia descoberta via FortiGate.

## Què fa

- ACL Manager es una aplicació que permet desplegar ACLs als fortiswitchos
- Està pensada per treballar a la branca 7.4 de FortiOS (Fortigate i Fortiswitchos).
- Permet definir les ACLs. Si el servei a filtrar no es troba per defecte als Fortiswitchos, es poden afegir serveis
  personalitzats (custom services).
- Permet excloure equips per evitar aplicar ACLs on no està previst. Es pot fer per IP o per model. Per exemple, podem
  excloure els equips de core
- Per defecte només s'aplica als ports d'usuari (per exemple ports 1-48 d'un 448E).
- Es podem congelar ports. Es a dir, ports on encara que apliquem ACLs al fortiswitch, quedaran exclosos. Pensat per 
  ports de servidors.
- Detecta automàticament els ports ISL/Fortilink/Trunk, per evitar aplicar ACLs en aquests tipus de ports.
- Els Fortiswitchos FS108F no soporten ACLs tipus Prelookup, son equips de sobretaula. Per no tenir un forat de seguretat,
  el commutador superior que dona servei al FS108F, si que aplica ACLs al port on es connecta el FS108F.
- Per gestionar Fortigates, cal tenir un API Token
- Per gestionar els fortiswitchos, cal tenir un usuari administrador. De moment no tenen implementat API Token.
- Una vegada desplegat ACLs, no es poden editar a la GUI dels fortiswitchos. Es un bug de FortiOS.

## Primera instal·lació

La base de dades es distribueix buida.

En el primer arrencada:

1. obre la web
2. seràs redirigit a `/setup`
3. crea el primer usuari local
4. després d'això, `/setup` desapareix i l'accés passa a ser només per `/login`

No existeix cap usuari per defecte.

## Configuració

Des de la pantalla `Settings` es poden editar:

- Campus i FortiGate IPs. 
- tokens API dels FortiGate
- restriccions per IP/model
- serveis custom
- ACLs `prelookup`
- usuari/contrasenya administrador de FortiSwitch

## Execució local

Des de l'arrel del projecte:

```bash
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker

La distribució Docker està pensada amb:

- contenidor `app`
- contenidor `nginx`
- només `HTTPS`
- només port `8499`

Rutes persistents previstes:

```text
data/
  certs/
    fullchain.pem
    privkey.pem
  config/
    config.yaml
  db/
    fortiswitch.db
  logs/
```

Variables de desplegament:

- `SERVER_NAME`
- `TLS_CERT_PATH`
- `TLS_KEY_PATH`
- `FORTI_API_CONFIG_PATH`
- `FORTI_API_DB_PATH`
- `FORTI_API_LOG_DIR`

Arrencada:

```bash
docker compose --env-file .env.docker up -d --build
```

Accés:

```text
https://<fqdn>:8499
```

