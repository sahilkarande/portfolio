import json

import pytest

from portfolio import create_app
from portfolio.commands import SEED_FILE, _seed
from portfolio.extensions import db
from portfolio.models import User

ADMIN_PASSWORD = "correct-horse-battery"


@pytest.fixture()
def app(tmp_path):
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = tmp_path / "uploads"
    with app.app_context():
        db.create_all()
        _seed(json.loads(SEED_FILE.read_text(encoding="utf-8")))
        user = User(username="admin")
        user.set_password(ADMIN_PASSWORD)
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin(client):
    resp = client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert resp.status_code == 302
    return client
