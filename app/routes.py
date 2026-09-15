"""Servicios y turnos."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .models import Appointment, Service, User, db

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _current_user() -> User | None:
    return db.session.get(User, int(get_jwt_identity()))


def _require_admin():
    user = _current_user()
    if user is None:
        return jsonify(error="no autenticado"), 401
    if not user.is_admin:
        return jsonify(error="se requiere rol admin"), 403
    return None


def _parse_start(value: str):
    try:
        start = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def _overlaps(service_id: int, start, end, exclude_id: int | None = None) -> bool:
    query = Appointment.query.filter(
        Appointment.service_id == service_id,
        Appointment.status != "cancelado",
    )
    if exclude_id is not None:
        query = query.filter(Appointment.id != exclude_id)
    for existing in query.all():
        service = existing.service
        existing_end = existing.start_at + timedelta(
            minutes=service.duration_minutes if service else 30
        )
        if start < existing_end and end > existing.start_at:
            return True
    return False


# --- Servicios -------------------------------------------------------------


@api_bp.get("/services")
def list_services():
    services = Service.query.filter_by(is_active=True).all()
    return jsonify([s.to_dict() for s in services])


@api_bp.post("/services")
@jwt_required()
def create_service():
    denied = _require_admin()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    try:
        duration = int(data.get("duration_minutes", 30))
        price = float(data.get("price", 0.0))
    except (TypeError, ValueError):
        return jsonify(error="duration_minutes y price deben ser numéricos"), 422
    if not name:
        return jsonify(error="name es obligatorio"), 422
    if duration <= 0 or price < 0:
        return jsonify(error="duration_minutes > 0 y price >= 0"), 422

    service = Service(
        name=name,
        description=(data.get("description") or "").strip(),
        duration_minutes=duration,
        price=price,
    )
    db.session.add(service)
    db.session.commit()
    return jsonify(service.to_dict()), 201


@api_bp.delete("/services/<int:service_id>")
@jwt_required()
def delete_service(service_id: int):
    denied = _require_admin()
    if denied:
        return denied
    service = db.session.get(Service, service_id)
    if service is None:
        return jsonify(error="servicio no encontrado"), 404
    service.is_active = False
    db.session.commit()
    return jsonify(message="servicio desactivado")


# --- Turnos ----------------------------------------------------------------


@api_bp.get("/appointments")
@jwt_required()
def list_appointments():
    user = _current_user()
    if user is None:
        return jsonify(error="no autenticado"), 401
    query = Appointment.query
    if not user.is_admin:
        query = query.filter_by(user_id=user.id)
    items = query.order_by(Appointment.start_at).all()
    return jsonify([a.to_dict() for a in items])


@api_bp.post("/appointments")
@jwt_required()
def book_appointment():
    user = _current_user()
    if user is None:
        return jsonify(error="no autenticado"), 401
    data = request.get_json(silent=True) or {}
    service = db.session.get(Service, data.get("service_id"))
    if service is None or not service.is_active:
        return jsonify(error="servicio no disponible"), 422

    start = _parse_start(data.get("start_at", ""))
    if start is None:
        return jsonify(error="start_at debe ser ISO 8601 válido"), 422
    if start <= datetime.now(timezone.utc).replace(tzinfo=None):
        return jsonify(error="el turno debe ser en el futuro"), 422

    end = start + timedelta(minutes=service.duration_minutes)
    if _overlaps(service.id, start, end):
        return jsonify(error="horario ocupado para ese servicio"), 409

    appointment = Appointment(
        user_id=user.id,
        service_id=service.id,
        start_at=start,
        notes=(data.get("notes") or "").strip(),
    )
    db.session.add(appointment)
    db.session.commit()
    return jsonify(appointment.to_dict()), 201


@api_bp.patch("/appointments/<int:appointment_id>/cancel")
@jwt_required()
def cancel_appointment(appointment_id: int):
    user = _current_user()
    if user is None:
        return jsonify(error="no autenticado"), 401
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None:
        return jsonify(error="turno no encontrado"), 404
    if not user.is_admin and appointment.user_id != user.id:
        return jsonify(error="no puedes cancelar turnos ajenos"), 403
    if appointment.status == "cancelado":
        return jsonify(error="el turno ya estaba cancelado"), 409
    appointment.status = "cancelado"
    db.session.commit()
    return jsonify(appointment.to_dict())
