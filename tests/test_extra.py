"""Cobertura P0/P1: autorización, validaciones, handlers y seed."""
from datetime import datetime, timedelta, timezone

from tests.conftest import _auth, _login, _make_admin, _register


def _future_iso(hours=48):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _setup_booked(client):
    """Admin + servicio + usuario con un turno reservado. Devuelve dict."""
    admin = _make_admin(client)
    service_id = (
        client.post(
            "/api/services",
            json={"name": "Corte", "duration_minutes": 30, "price": 100.0},
            headers=_auth(admin),
        ).get_json()["id"]
    )
    _register(client, name="Cli", email="cli@mail.com")
    token = _login(client, email="cli@mail.com")
    appt = client.post(
        "/api/appointments",
        json={"service_id": service_id, "start_at": _future_iso()},
        headers=_auth(token),
    ).get_json()
    return {"admin": admin, "token": token, "service_id": service_id, "appt": appt}


def test_cancelar_turno_ajeno_403(client):
    ctx = _setup_booked(client)
    _register(client, name="Otro", email="otro@mail.com")
    token_otro = _login(client, email="otro@mail.com")
    res = client.patch(
        f"/api/appointments/{ctx['appt']['id']}/cancel",
        headers=_auth(token_otro),
    )
    assert res.status_code == 403
    assert "error" in res.get_json()


def test_admin_cancela_turno_ajeno_200(client):
    ctx = _setup_booked(client)
    res = client.patch(
        f"/api/appointments/{ctx['appt']['id']}/cancel",
        headers=_auth(ctx["admin"]),
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "cancelado"


def test_doble_cancelacion_409(client):
    ctx = _setup_booked(client)
    url = f"/api/appointments/{ctx['appt']['id']}/cancel"
    assert client.patch(url, headers=_auth(ctx["token"])).status_code == 200
    res = client.patch(url, headers=_auth(ctx["token"]))
    assert res.status_code == 409


def test_cancelar_inexistente_404_y_sin_token_401(client):
    ctx = _setup_booked(client)
    assert (
        client.patch(
            "/api/appointments/9999/cancel", headers=_auth(ctx["token"])
        ).status_code
        == 404
    )
    res = client.patch(f"/api/appointments/{ctx['appt']['id']}/cancel")
    assert res.status_code == 401


def test_cancelar_pasado_409(client):
    from app.models import Appointment, Service, User, db

    admin = _make_admin(client)
    service_id = (
        client.post(
            "/api/services",
            json={"name": "Corte", "duration_minutes": 30, "price": 100.0},
            headers=_auth(admin),
        ).get_json()["id"]
    )
    _register(client)
    token = _login(client)
    with client.application.app_context():
        user = User.query.filter_by(email="juan@mail.com").first()
        service = db.session.get(Service, service_id)
        past = Appointment(
            user_id=user.id,
            service_id=service.id,
            start_at=datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(hours=1),
        )
        db.session.add(past)
        db.session.commit()
        past_id = past.id
    res = client.patch(
        f"/api/appointments/{past_id}/cancel", headers=_auth(token)
    )
    assert res.status_code == 409


def test_delete_servicio_ciclo(client):
    admin = _make_admin(client)
    assert client.delete("/api/services/1").status_code == 401
    _register(client)
    token = _login(client)
    sid = (
        client.post(
            "/api/services",
            json={"name": "X", "duration_minutes": 10, "price": 1.0},
            headers=_auth(admin),
        ).get_json()["id"]
    )
    assert client.delete(f"/api/services/{sid}", headers=_auth(token)).status_code == 403
    assert client.delete("/api/services/9999", headers=_auth(admin)).status_code == 404
    assert client.delete(f"/api/services/{sid}", headers=_auth(admin)).status_code == 200
    assert client.get("/api/services").get_json() == []


def test_delete_servicio_con_futuros_409(client):
    ctx = _setup_booked(client)
    res = client.delete(
        f"/api/services/{ctx['service_id']}", headers=_auth(ctx["admin"])
    )
    assert res.status_code == 409
    assert "futuro" in res.get_json()["error"]


def test_start_at_invalido_422_y_formatos_ok(client):
    ctx = _setup_booked(client)
    for bad in ["no-fecha", "", None]:
        res = client.post(
            "/api/appointments",
            json={"service_id": ctx["service_id"], "start_at": bad},
            headers=_auth(ctx["token"]),
        )
        assert res.status_code == 422
    # naive se asume UTC y Zulu se acepta
    naive = (datetime.now(timezone.utc) + timedelta(hours=72)).replace(
        tzinfo=None
    ).isoformat()
    res = client.post(
        "/api/appointments",
        json={"service_id": ctx["service_id"], "start_at": naive},
        headers=_auth(ctx["token"]),
    )
    assert res.status_code == 201
    assert res.get_json()["start_at"].endswith("+00:00")
    zulu = (datetime.now(timezone.utc) + timedelta(hours=96)).isoformat().replace(
        "+00:00", "Z"
    )
    res = client.post(
        "/api/appointments",
        json={"service_id": ctx["service_id"], "start_at": zulu},
        headers=_auth(ctx["token"]),
    )
    assert res.status_code == 201


def test_reservar_servicio_inexistente_o_invalido_422(client):
    ctx = _setup_booked(client)
    for bad_id in [9999, "abc", None]:
        res = client.post(
            "/api/appointments",
            json={"service_id": bad_id, "start_at": _future_iso()},
            headers=_auth(ctx["token"]),
        )
        assert res.status_code == 422


def test_solape_parcial_409_y_adyacente_201(client):
    ctx = _setup_booked(client)
    base = datetime.fromisoformat(ctx["appt"]["start_at"])
    solape = (base + timedelta(minutes=15)).isoformat()
    res = client.post(
        "/api/appointments",
        json={"service_id": ctx["service_id"], "start_at": solape},
        headers=_auth(ctx["token"]),
    )
    assert res.status_code == 409
    adyacente = (base + timedelta(minutes=30)).isoformat()
    res = client.post(
        "/api/appointments",
        json={"service_id": ctx["service_id"], "start_at": adyacente},
        headers=_auth(ctx["token"]),
    )
    assert res.status_code == 201


def test_crear_servicio_validaciones_422(client):
    admin = _make_admin(client)
    cases = [
        {"name": "", "duration_minutes": 30, "price": 1},
        {"name": "X", "duration_minutes": 0, "price": 1},
        {"name": "X", "duration_minutes": -5, "price": 1},
        {"name": "X", "duration_minutes": "abc", "price": 1},
        {"name": "X", "duration_minutes": 30, "price": -1},
        {"name": "X", "duration_minutes": 30, "price": "abc"},
        {"name": "X" * 121, "duration_minutes": 30, "price": 1},
    ]
    for payload in cases:
        res = client.post(
            "/api/services", json=payload, headers=_auth(admin)
        )
        assert res.status_code == 422, payload


def test_login_email_inexistente_401(client):
    res = client.post(
        "/api/auth/login", json={"email": "nadie@mail.com", "password": "x" * 10}
    )
    assert res.status_code == 401


def test_appointments_sin_token_401(client):
    assert client.get("/api/appointments").status_code == 401
    assert (
        client.post(
            "/api/appointments", json={"service_id": 1, "start_at": _future_iso()}
        ).status_code
        == 401
    )


def test_register_no_escala_admin_ni_expone_hash(client):
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Vivo",
            "email": "vivo@mail.com",
            "password": "secreto1",
            "is_admin": True,
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["is_admin"] is False
    assert "password_hash" not in body
    assert "password" not in body


def test_health_y_404_json(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    res = client.get("/ruta-inexistente")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_seed_idempotente(client):
    runner = client.application.test_cli_runner()
    for _ in range(2):
        result = runner.invoke(args=["seed"])
        assert result.exit_code == 0
        assert "Seed OK" in result.output
    with client.application.app_context():
        from app.models import Service, User

        assert User.query.filter_by(email="admin@turnos.local").count() == 1
        assert Service.query.count() == 3
