# Despliegue

Estrategia de referencia: **Docker Compose** ([ADR 0002](decisions/0002-runtime-and-deployment-strategy.md)).
La ejecución nativa permanece soportada ([development.md](development.md)).

## Servicios

| Servicio | Rol |
|----------|-----|
| `exceler-app` | API FastAPI, CLI, migraciones, lógica de aplicación |
| `exceler-db` | PostgreSQL 16 (red interna; sin puerto publicado al host por defecto) |

## Arranque

```bash
cp .env.example .env
cp secrets/db_password.example secrets/db_password
# editar secrets/db_password

docker compose up --build
```

Aplicar migraciones (no se ejecutan solas en producción):

```bash
docker compose exec exceler-app exceler db upgrade
```

Comprobar salud:

```bash
curl http://127.0.0.1:8000/health
```

Parar:

```bash
docker compose down
```

Pruebas dentro del contenedor:

```bash
docker compose exec exceler-app pytest
```

## Volúmenes

- `exceler_db_data` — datos PostgreSQL.
- `exceler_work` — trabajo escribible.
- `exceler_tmp` — temporales.
- `./samples/sources:/sources/samples:ro` — origen sintético de ejemplo.

Montajes corporativos reales no se versionan. Usar `docker-compose.override.yml` (ver `docker-compose.override.example.yml`):

```yaml
services:
  exceler-app:
    volumes:
      - /mnt/comercial:/sources/comercial:ro
```

EXCELER registra rutas **internas** (`/sources/...`). En esta fase, SMB/autenticación de red la gestiona el host.

## Seguridad del contenedor `exceler-app`

- usuario no root `exceler`;
- `read_only: true` + tmpfs `/tmp` + volúmenes de escritura explícitos;
- `cap_drop: ALL`;
- `no-new-privileges:true`;
- sin `privileged` ni socket Docker;
- orígenes `:ro`;
- secretos vía Docker secrets en `/run/secrets/`.

## Secretos

Ver [configuration.md](configuration.md). Nunca versionar `.env` ni `secrets/db_password`.

## Excepciones documentadas

- El puerto HTTP de la API se publica al host (`8000`) para desarrollo local.
- PostgreSQL **no** se publica al host por defecto.
- `EXCELER_API_DEV_TOKEN` es un gate opcional de desarrollo, no autenticación de producto.
