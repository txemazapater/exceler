# Despliegue

Estrategia de referencia: **Docker Compose** en **Server Host** ([ADR 0002](decisions/0002-runtime-and-deployment-strategy.md), [ADR 0004](decisions/0004-execution-hosts-and-nodes.md)).
Native / Desktop / Agent son hosts adicionales documentados; no se asume que todo origen sea accesible desde el servidor central.

## Servicios

| Servicio | Rol |
|----------|-----|
| `exceler-app` | API FastAPI, CLI, migraciones, lógica de aplicación |
| `exceler-db` | PostgreSQL 16 (red interna; sin puerto publicado al host por defecto) |

La imagen instala dependencias con **`uv sync --frozen`** desde `uv.lock`.

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
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

- Compose healthcheck de `exceler-app` → `/health/ready`
- HEALTHCHECK de imagen → `/health/live`
- `/health` permanece como alias de liveness

Parar:

```bash
docker compose down
```

## Volúmenes

- `exceler_db_data` — datos PostgreSQL.
- `exceler_work` — trabajo escribible.
- `exceler_tmp` — temporales.
- `./samples/sources:/sources/samples:ro` — origen sintético de ejemplo.

Montajes corporativos reales no se versionan. Usar `docker-compose.override.yml`.

Preferir nombres de **servicio** (`exceler-app`, `exceler-db`) y un project name explícito:

```bash
docker compose -p exceler exec exceler-app exceler db upgrade
```

No hay `container_name` fijos: se pueden ejecutar varias copias aisladas (`-p exceler-ci`, `-p exceler`, etc.).

Staging en SAPIENS (Traefik, sin publicar HTTP al host): [staging.md](staging.md) y `compose.staging.yaml`.

## Seguridad del contenedor `exceler-app`

- usuario no root `exceler`;
- `read_only: true` + tmpfs `/tmp` + volúmenes de escritura explícitos;
- `cap_drop: ALL`;
- `no-new-privileges:true`;
- orígenes `:ro`;
- secretos vía Docker secrets en `/run/secrets/`.

## Secretos

Ver [configuration.md](configuration.md). Nunca versionar `.env` ni `secrets/db_password`.

## Excepciones documentadas

- El puerto HTTP de la API se publica al host (`8000`) para desarrollo local.
- PostgreSQL **no** se publica al host por defecto.
- `EXCELER_API_DEV_TOKEN` es un gate opcional de desarrollo, no autenticación de producto.
