"""Factory de la aplicación Flask."""
import click
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager

from config import Config

from .models import Service, User, db

DEV_SECRET = "dev-secret-change-me"
DEV_JWT = "dev-jwt-change-me"


def _seed_demo_data() -> None:
    """Crea admin + servicios de ejemplo (idempotente)."""
    db.create_all()
    admin_email = Config.ADMIN_EMAIL
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name="Admin", email=admin_email, is_admin=True)
        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)
    if Service.query.count() == 0:
        db.session.add_all(
            [
                Service(
                    name="Corte de cabello",
                    description="Corte clásico o moderno.",
                    duration_minutes=30,
                    price=5000.0,
                ),
                Service(
                    name="Barba",
                    description="Perfilado y afeitado.",
                    duration_minutes=20,
                    price=3000.0,
                ),
                Service(
                    name="Corte + barba",
                    description="Servicio completo.",
                    duration_minutes=50,
                    price=7000.0,
                ),
            ]
        )
    db.session.commit()


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get("ENV") == "production":
        if app.config["SECRET_KEY"] == DEV_SECRET:
            raise RuntimeError("SECRET_KEY requerida en producción")
        if app.config["JWT_SECRET_KEY"] == DEV_JWT:
            raise RuntimeError("JWT_SECRET_KEY requerida en producción")

    db.init_app(app)
    JWTManager(app)

    from .auth import auth_bp
    from .routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        if app.config.get("SEED_DEMO", False):
            _seed_demo_data()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Recurso no encontrado"), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(error="Método no permitido"), 405

    @app.cli.command("seed")
    def seed() -> None:
        """Crea admin + servicios de ejemplo (idempotente)."""
        with app.app_context():
            _seed_demo_data()
            click.echo(f"Seed OK: {app.config.get('ADMIN_EMAIL', Config.ADMIN_EMAIL)}")

    return app
