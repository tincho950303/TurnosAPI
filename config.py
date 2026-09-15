"""Configuración por entorno via variables de entorno."""
import os
from datetime import timedelta


class Config:
    ENV = os.environ.get("FLASK_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///turnos.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEED_DEMO = os.environ.get("SEED_DEMO", "true") == "true"
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@turnos.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Render entrega postgres:// pero SQLAlchemy espera postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
