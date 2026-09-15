"""Punto de entrada (gunicorn wsgi:app / flask --app wsgi)."""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug solo explícito en desarrollo; gunicorn/prod nunca pasan por aquí
    app.run(host="0.0.0.0", port=8000, debug=os.getenv("FLASK_DEBUG") == "1")
