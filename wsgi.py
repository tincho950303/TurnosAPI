"""Punto de entrada (gunicorn wsgi:app / flask --app wsgi)."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
