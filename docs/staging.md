# Staging en SAPIENS

SAPIENS es un host Linux remoto con Docker usado como **staging de integración** para EXCELER.

No se despliega automáticamente desde CI. El procedimiento es **manual** hasta que sea estable, repetible y seguro.

## Propósito

- pruebas manuales de despliegue;
- validación real de volúmenes;
- integración con Traefik;
- persistencia entre reinicios;
- pruebas de actualización;
- análisis posterior de fuentes sintéticas;
- futura demostración interna.

## Estructura sugerida en el host

```text
/opt/stacks/exceler/
├── compose.yaml                 # enlace o copia del docker-compose.yml del repo
├── compose.staging.yaml         # overlay Traefik / staging
├── .env                         # no versionar; valores de SAPIENS
├── secrets/
│   └── db_password
├── sources/                     # montajes sintéticos o autorizados (:ro)
└── work/
```

Clonar o sincronizar el repositorio en una ruta de trabajo y apuntar los ficheros Compose hacia ella, o trabajar directamente desde el checkout:

```text
/opt/stacks/exceler/repo/   # git clone
```

## Variables típicas (ejemplo)

```bash
EXCELER_ENV=staging
EXCELER_PUBLIC_HOST=exceler.example.internal
EXCELER_TRAEFIK_NETWORK=traefik
EXCELER_TRAEFIK_ENTRYPOINT=websecure
EXCELER_TRAEFIK_ROUTER=exceler
EXCELER_SOURCES_HOST_PATH=/opt/stacks/exceler/sources
```

Usar solo secretos sintéticos o de entorno de staging. Nunca datos corporativos reales en el repositorio.

## Procedimiento manual

Desde el directorio del stack (o del repo):

```bash
git pull
cp secrets/db_password.example secrets/db_password   # solo la primera vez / rotación
# editar .env y secrets/db_password

docker compose -p exceler -f docker-compose.yml -f compose.staging.yaml build
docker compose -p exceler -f docker-compose.yml -f compose.staging.yaml up -d
docker compose -p exceler exec exceler-app exceler db upgrade
docker compose -p exceler ps

curl http://127.0.0.1:8000/health/live    # si el puerto sigue publicado en un override local
curl http://127.0.0.1:8000/health/ready
```

Con Traefik y `compose.staging.yaml`, el puerto host puede no publicarse; usar entonces la URL pública configurada:

```bash
curl https://$EXCELER_PUBLIC_HOST/health/live
curl https://$EXCELER_PUBLIC_HOST/health/ready
```

## Notas operativas

- Preferir nombres de **servicio** (`exceler-app`, `exceler-db`), no `container_name` fijos.
- Usar `-p exceler` (u otro project name) para aislar staging de pruebas CI.
- PostgreSQL permanece en la red interna; no exponerlo al host.
- Fuentes montadas siempre `:ro`.
- Tras un fallo: `docker compose -p exceler logs exceler-app exceler-db`.

## Relación con CI

GitHub Actions valida build y un smoke test de Compose desde cero.
SAPIENS valida el despliegue real (Traefik, volúmenes, reinicios) de forma manual.

Ver también [deployment.md](deployment.md) y [ADR 0004](decisions/0004-execution-hosts-and-nodes.md).
