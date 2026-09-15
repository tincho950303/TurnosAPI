from datetime import datetime, timedelta, timezone

from tests.conftest import _auth, _login, _make_admin, _register


def _future_iso(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _create_service(client, token, name="Corte"):
    return client.post(
        "/api/services",
        json={"name": name, "duration_minutes": 30, "price": 100.0},
        headers=_auth(token),
    )


def test_register_y_login_ok(client):
    assert _register(client).status_code == 201
    res = client.post(
        "/api/auth/login", json={"email": "juan@mail.com", "password": "secreto1"}
    )
    assert res.status_code == 200
    assert "access_token" in res.get_json()


def test_register_duplicado_409(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 409


def test_register_datos_invalidos_422(client):
    assert client.post("/api/auth/register", json={}).status_code == 422
    assert _register(client, email="no-es-email").status_code == 422
    assert _register(client, email="otro@mail.com", password="123").status_code == 422


def test_login_invalido_401(client):
    _register(client)
    res = client.post(
        "/api/auth/login", json={"email": "juan@mail.com", "password": "mal"}
    )
    assert res.status_code == 401


def test_crear_servicio_requiere_admin(client):
    _register(client)
    token = _login(client)
    # usuario común -> 403
    assert _create_service(client, token).status_code == 403
    # sin token -> 401
    assert client.post("/api/services", json={"name": "X"}).status_code == 401


def test_admin_crea_y_lista_servicios(client):
    admin = _make_admin(client)
    assert _create_service(client, admin).status_code == 201
    res = client.get("/api/services")
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_reservar_turno_ok(client):
    admin = _make_admin(client)
    service_id = _create_service(client, admin).get_json()["id"]
    _register(client)
    token = _login(client)
    res = client.post(
        "/api/appointments",
        json={"service_id": service_id, "start_at": _future_iso()},
        headers=_auth(token),
    )
    assert res.status_code == 201
    assert res.get_json()["status"] == "pendiente"


def test_doble_reserva_409(client):
    admin = _make_admin(client)
    service_id = _create_service(client, admin).get_json()["id"]
    _register(client)
    token = _login(client)
    payload = {"service_id": service_id, "start_at": _future_iso()}
    assert client.post("/api/appointments", json=payload, headers=_auth(token)).status_code == 201
    assert client.post("/api/appointments", json=payload, headers=_auth(token)).status_code == 409


def test_turno_en_pasado_422(client):
    admin = _make_admin(client)
    service_id = _create_service(client, admin).get_json()["id"]
    _register(client)
    token = _login(client)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    res = client.post(
        "/api/appointments",
        json={"service_id": service_id, "start_at": past},
        headers=_auth(token),
    )
    assert res.status_code == 422


def test_cancelar_turno_y_reusar_horario(client):
    admin = _make_admin(client)
    service_id = _create_service(client, admin).get_json()["id"]
    _register(client)
    token = _login(client)
    payload = {"service_id": service_id, "start_at": _future_iso()}
    appt_id = client.post(
        "/api/appointments", json=payload, headers=_auth(token)
    ).get_json()["id"]
    res = client.patch(
        f"/api/appointments/{appt_id}/cancel", headers=_auth(token)
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "cancelado"
    # horario liberado
    assert client.post("/api/appointments", json=payload, headers=_auth(token)).status_code == 201


def test_usuarios_solo_ven_sus_turnos(client):
    admin = _make_admin(client)
    service_id = _create_service(client, admin).get_json()["id"]
    _register(client, email="a@mail.com")
    token_a = _login(client, email="a@mail.com")
    _register(client, name="B", email="b@mail.com")
    token_b = _login(client, email="b@mail.com")
    client.post(
        "/api/appointments",
        json={"service_id": service_id, "start_at": _future_iso()},
        headers=_auth(token_a),
    )
    mine = client.get("/api/appointments", headers=_auth(token_b)).get_json()
    assert mine == []
    all_items = client.get("/api/appointments", headers=_auth(admin)).get_json()
    assert len(all_items) == 1
