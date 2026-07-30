# Configuración

## Fuentes

Preferencia: variables de entorno (y secretos montados). Archivos de ejemplo:

- `.env.example`
- `config.example.yaml`
- `docker-compose.override.example.yml`
- `secrets/db_password.example`

## Variables principales

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL SQLAlchemy completa (alternativa a piezas) |
| `DATABASE_URL_REF` | Referencia `env://` o `file://` a la URL |
| `EXCELER_DB_HOST` / `PORT` / `NAME` / `USER` | Piezas de conexión |
| `EXCELER_DB_PASSWORD` | Contraseña en claro (solo local) |
| `EXCELER_DB_PASSWORD_REF` | `file:///run/secrets/db_password` o `env://...` |
| `EXCELER_ALLOWED_SOURCE_ROOTS` | Raíces permitidas separadas por comas |
| `EXCELER_LOG_LEVEL` | Nivel de log |
| `EXCELER_AUTO_MIGRATE` | Reservado; migraciones se aplican vía CLI |
| `EXCELER_API_DEV_TOKEN` | Gate opcional; header `X-Exceler-Token` |

## Referencias de secretos

```text
file:///run/secrets/db_password
env://EXCELER_DB_PASSWORD
```

La aplicación resuelve la referencia en tiempo de ejecución. Los logs redactan claves sensibles.

`credential_reference` en un `DiscoverySource` guarda **solo** la referencia, nunca el secreto.

## Qué no versionar

- `.env`
- `secrets/db_password`
- `docker-compose.override.yml`
- dumps, certificados, rutas corporativas reales
