# Instrucciones para agentes

## Alcance del proyecto

TurnosAPI es una API REST con Flask para gestionar turnos y reservas. Registro/login
con JWT, roles admin/usuario, alta de servicios y reserva de turnos con validación
de solapamientos. SQLite local, Postgres en producción vía `DATABASE_URL`. Consulta
el [README](README.md) para la explicación funcional completa.

## Mapa de responsabilidades

- `wsgi.py`: punto de entrada (`gunicorn wsgi:app`); el bloque `__main__` es solo
  desarrollo y nunca activa debug salvo `FLASK_DEBUG=1`.
- `config.py`: configuración por variables de entorno. En producción (`FLASK_ENV=production`)
  falla si `SECRET_KEY`/`JWT_SECRET_KEY` siguen siendo los valores de desarrollo.
- `app/__init__.py`: factory `create_app`, blueprints, handlers JSON 404/405,
  comando `flask seed` y auto-seed demo (`SEED_DEMO=true` + BD vacía).
- `app/models.py`: `User`, `Service`, `Appointment`. Borrado siempre lógico
  (`status=cancelado`, `is_active=False`); nunca `DELETE` físico.
- `app/auth.py`: registro y login. `is_admin` NO se acepta del cliente.
- `app/routes.py`: servicios y turnos. `_overlaps()` excluye cancelados.
- `tests/`: suite pytest (27 tests). `conftest.py` trae fixtures y helpers
  (`_register`, `_login`, `_auth`, `_make_admin`); no duplicar helpers en
  archivos de test.
- `requirements.txt` (prod) / `requirements-dev.txt` (prod + pytest).
- `Dockerfile`, `docker-compose.yml`, `render.yaml`: deploy local y en Render.

## Convenciones de trabajo

- Fechas: convención **naive en UTC** en base de datos; se acepta ISO con `Z` u
  offset y se expone con sufijo `+00:00`. No mezclar aware/naive.
- Cancelar libera el horario (el cancelado se excluye de `_overlaps`): no añadir
  `UniqueConstraint(service_id, start_at)` porque rompería el reuso. La condición
  de carrera residual es limitación conocida (ver roadmap).
- Desactivar un servicio con turnos futuros debe dar `409`, no borrarlos.
- Códigos: `201` crear, `401` sin token, `403` sin permiso o recurso ajeno,
  `404` inexistente, `409` conflicto de negocio, `422` validación.
- JWT `identity` es `str(user.id)`; siempre re-consultar el usuario en BD, nunca
  confiar en claims de rol. Envolver `int(identity)` en try/except.
- El seed demo corre en el arranque de cada worker gunicorn: debe seguir siendo
  idempotente y tolerante a carreras (rollback + reintento con backoff ante
  `IntegrityError`/`OperationalError`). No poblar con `INSERT` sin re-chequeo.
- Respuestas de error siempre JSON con clave `error`; no exponer trazas ni hashes.
- Cambios pequeños y enfocados; no reformatees archivos no relacionados.
- No commits, push ni ramas nuevas salvo petición explícita.
- No expongas ni commitees secretos (`.env`, `instance/`, `*.db` están ignorados).

## Ejecución y validación

Desde la raíz del proyecto:

```powershell
pip install -r requirements-dev.txt
flask --app wsgi seed
flask --app wsgi run        # http://localhost:5000
python -m pytest tests -q   # 27 tests, 0 warnings es el estándar
docker compose up --build   # http://localhost:8000
```

Seed demo: `admin@turnos.local / admin123` (o `ADMIN_EMAIL`/`ADMIN_PASSWORD`).
Antes de terminar: `pytest -q` en verde y, si tocaste Docker, smoke test a
`/health` en contenedor.

## Protocolo multi-agente (revisión cruzada)

Para cambios no triviales, separa la validación en subagentes que se controlan
entre sí antes de commitear. Invócalos en paralelo con la herramienta Task:

1. **Seguridad backend** (`general`): audita `app/`, `config.py`, `wsgi.py`.
   Busca secretos, mass assignment, authz rota, validaciones, timezones, race
   conditions. Solo reporta (severidad + archivo:línea + fix), no edita.
2. **QA tests** (`general`): corre `pytest`, mapea gaps contra `routes.py`/`auth.py`
   (autorización 403, 404/409/422, handlers, seed). Solo reporta, no edita.
3. **DevOps/release** (`general`): `git ls-files` sin artefactos, `docker compose
   config`, coherencia `Dockerfile`/`render.yaml`/`requirements`/`README`.
   Solo reporta, no edita ni pushea.

El implementador aplica los fixes de alto valor, re-corre la suite y recién ahí
commitea. Decisiones arquitectónicas que se tomaron con este protocolo y no hay
que revertir sin discutir: sin `UniqueConstraint` en turnos (borrado lógico +
reuso), sin Postgres en `render.yaml` (SQLite + auto-seed para demo efímera),
`requirements` separadas prod/dev.

## Roadmap conocido (no reintroducir como bug)

Rate limiting en auth, paginación en listados, `EXCLUDE` de Postgres contra la
condición de carrera, precio `Numeric`, horizonte de reserva y horario laboral.
