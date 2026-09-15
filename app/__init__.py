"""Factory de la aplicación Flask."""
import click
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager

from config import Config

from .models import Service, User, db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    JWTManager(app)

    from .auth import auth_bp
    from .routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

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
            db.create_all()
            if not User.query.filter_by(email="admin@turnos.local").first():
                admin = User(name="Admin", email="admin@turnos.local", is_admin=True)
                admin.set_password("admin123")
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
            click.echo("Seed OK: admin@turnos.local / admin123")

    return app
