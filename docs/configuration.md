# Configuración

## Fuentes

Preferencia: variables de entorno (y secretos montados). Archivos de ejemplo:

- `.env.example`
- `config.example.yaml`
- `docker-compose.override.example.yml`
- `secrets/db_password.example`

`pyproject.toml` declara rangos de dependencias; **`uv.lock`** fija la resolución reproducible.

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

## Referencias de secretos y `credential_reference`

Esquemas aceptados:

```text
env://VARIABLE_NAME
file:///absolute/path/to/secret
```

Reservados para fases futuras (rechazados hoy): `vault://`, `keyring://`, `secret-manager://`.

Reglas:

- no se aceptan secretos desnudos;
- la API persiste y devuelve **solo la referencia**, nunca el valor resuelto;
- los logs no incluyen contenido secreto;
- una referencia puede no resolverse en el Server Host si pertenece a otro nodo (futuro Agent Host).

## Qué no versionar

- `.env`
- `secrets/db_password`
- `docker-compose.override.yml`
- dumps, certificados, rutas corporativas reales
