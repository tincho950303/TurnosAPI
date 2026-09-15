import pytest

from app import create_app
from app.models import db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-32-chars-minimum-ok"
    JWT_SECRET_KEY = "test-jwt-key-32-chars-minimum-ok!"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _register(client, name="Juan", email="juan@mail.com", password="secreto1"):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def _login(client, email="juan@mail.com", password="secreto1"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_admin(client, email="admin@mail.com", password="secreto1"):
    from app.models import User, db

    _register(client, name="Admin", email=email, password=password)
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        user.is_admin = True
        db.session.commit()
    return _login(client, email=email, password=password)
