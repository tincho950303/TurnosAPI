# TurnosAPI

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-black?logo=flask&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

API REST para gestionar **turnos y reservas** (barberías, consultorios, servicios). Registro y login con JWT, roles admin/usuario, alta de servicios y reserva de turnos con validación de solapamientos. Incluye 11 tests automatizados y deploy en un clic.

## Características

- Registro/login con contraseñas hasheadas (Werkzeug) y tokens JWT.
- Roles: `admin` crea y desactiva servicios; usuarios reservan y cancelan sus turnos.
- Validaciones: email, password ≥ 6, fechas futuras, servicio activo, **sin doble reserva** (409), cancelación libera el horario.
- Respuestas JSON consistentes con códigos HTTP correctos (201/401/403/404/409/422).
- 11 tests pytest (auth, permisos, reservas, conflictos, privacidad de datos).
- Sin estado en memoria: SQLite local, Postgres en producción vía `DATABASE_URL`.

## Stack

| Capa | Tecnología |
|---|---|
| Framework | Flask 3.1 |
| ORM | Flask-SQLAlchemy 3 + SQLAlchemy 2 |
| Auth | Flask-JWT-Extended |
| Tests | pytest |
| Servidor prod | gunicorn |
| Deploy | Docker + Render (`render.yaml`) |

## Inicio rápido

```powershell
pip install -r requirements.txt
flask --app wsgi seed      # crea admin@turnos.local / admin123 + servicios ejemplo
flask --app wsgi run       # http://localhost:5000
```

```powershell
# Con Docker
docker compose up --build  # http://localhost:8000
```

```powershell
# Tests
pytest -q
```

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | — | Estado del servicio |
| POST | `/api/auth/register` | — | Registro (`name`, `email`, `password`) |
| POST | `/api/auth/login` | — | Login, devuelve `access_token` |
| GET | `/api/services` | — | Servicios activos |
| POST | `/api/services` | admin | Crear servicio |
| DELETE | `/api/services/<id>` | admin | Desactivar servicio |
| GET | `/api/appointments` | JWT | Mis turnos (admin ve todos) |
| POST | `/api/appointments` | JWT | Reservar (`service_id`, `start_at` ISO) |
| PATCH | `/api/appointments/<id>/cancel` | JWT | Cancelar turno propio (o admin) |

Ejemplo:

```powershell
$body = @{ email = "admin@turnos.local"; password = "admin123" } | ConvertTo-Json
$login = Invoke-RestMethod http://localhost:5000/api/auth/login -Method Post -Body $body -ContentType "application/json"
$login.access_token
```

## Estructura

| Archivo | Rol |
|---|---|
| `wsgi.py` | Entrada (`gunicorn wsgi:app`) |
| `config.py` | Configuración por variables de entorno |
| `app/__init__.py` | Factory, blueprints, comando `flask seed` |
| `app/models.py` | `User`, `Service`, `Appointment` |
| `app/auth.py` | Registro y login |
| `app/routes.py` | Servicios y turnos |
| `tests/` | Suite pytest (11 tests) |
| `render.yaml` | Deploy en Render con secretos generados |

## Deploy en Render

New → Web Service desde el repo (detecta `render.yaml`), o manual: Runtime Python, build `pip install -r requirements.txt`, start `gunicorn wsgi:app`.

## Licencia

MIT — ver [LICENSE](LICENSE).
