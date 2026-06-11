"""Pytest configuration and fixtures."""

import os
import pytest

from app import create_app
from extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create a test app with an in-memory SQLite database."""
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    app, socketio = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.app_context():
        _db.create_all()

    yield app

    with app.app_context():
        _db.drop_all()


@pytest.fixture
def client(app):
    """HTTP test client."""
    return app.test_client()


@pytest.fixture
def socketio_client(app):
    """SocketIO test client."""
    from extensions import socketio
    return socketio.test_client(app)


@pytest.fixture
def db(app):
    """Database session fixture."""
    with app.app_context():
        yield _db
