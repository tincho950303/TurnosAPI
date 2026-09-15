"""Registro y login con JWT."""
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from .models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify(error="name, email y password son obligatorios"), 422
    if len(name) > 120 or len(email) > 160 or len(password) > 128:
        return jsonify(error="campos exceden la longitud máxima"), 422
    if not EMAIL_RE.match(email):
        return jsonify(error="email inválido"), 422
    if len(password) < 6:
        return jsonify(error="password debe tener al menos 6 caracteres"), 422
    if User.query.filter_by(email=email).first():
        return jsonify(error="ese email ya está registrado"), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify(error="credenciales inválidas"), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, user=user.to_dict())
