from unittest.mock import patch

import pytest

from portfolio.extensions import db
from portfolio.models import Message, Project


@pytest.mark.parametrize("path", ["/", "/resume", "/projects", "/certificates", "/blogs", "/contact"])
def test_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"Sahil Karande" in resp.data


def test_404(client):
    assert client.get("/nope").status_code == 404


def test_projects_page_uses_db_and_hides_unpublished(client, app):
    project = db.session.scalars(db.select(Project).order_by(Project.sort_order)).first()
    assert project.title.encode() in client.get("/projects").data
    project.is_published = False
    db.session.commit()
    assert project.title.encode() not in client.get("/projects").data


def test_skill_group_order_preserved(client):
    html = client.get("/resume").get_data(as_text=True)
    assert html.index("Big Data Technologies") < html.index("Soft Skills")


def _post(client, **overrides):
    data = {"fullname": "Peter Parker", "email": "peter@example.com", "phone": "",
            "message": "Hello <b>there</b>, nice site!"}
    data.update(overrides)
    return client.post("/contact", data=data, follow_redirects=True)


@patch("portfolio.public.routes.send_contact_emails", return_value=False)
def test_contact_saves_message_even_if_email_fails(mock_send, client):
    resp = _post(client)
    assert b"Message sent successfully" in resp.data
    msg = db.session.scalars(db.select(Message)).one()
    assert msg.name == "Peter Parker" and msg.email_sent is False
    mock_send.assert_called_once()


@patch("portfolio.public.routes.send_contact_emails", return_value=True)
def test_contact_honeypot_discards(mock_send, client):
    _post(client, website="http://spam.example")
    assert db.session.scalar(db.select(db.func.count(Message.id))) == 0
    mock_send.assert_not_called()


@patch("portfolio.public.routes.send_contact_emails", return_value=True)
def test_contact_rate_limited(mock_send, client):
    for _ in range(3):
        _post(client)
    resp = _post(client)
    assert b"several messages recently" in resp.data
    assert db.session.scalar(db.select(db.func.count(Message.id))) == 3


def test_contact_validation_error(client):
    resp = _post(client, email="not-an-email")
    assert b"Please check the form" in resp.data
    assert db.session.scalar(db.select(db.func.count(Message.id))) == 0


def test_email_templates_escape_visitor_input(app):
    from flask import render_template
    msg = Message(name="<script>x</script>", email="a@b.c", body="<img src=x onerror=alert(1)>")
    with app.test_request_context():
        html = render_template("email/owner_notification.html", message=msg)
    assert "<script>" not in html and "&lt;img" in html


def test_projects_rendered_server_side_with_filters(client, app):
    html = client.get("/projects").get_data(as_text=True)
    published = db.session.scalar(db.select(db.func.count(Project.id)).where(Project.is_published.is_(True)))
    assert html.count("data-item") == published
    assert 'data-filter="data-science"' in html and 'data-filter="web-development"' in html


def test_project_text_is_escaped(client, app):
    p = db.session.scalars(db.select(Project)).first()
    p.title = "<script>alert(1)</script>"
    db.session.commit()
    html = client.get("/projects").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_resume_shows_duration_and_current_role(client):
    html = client.get("/resume").get_data(as_text=True)
    assert "1 mo" in html  # Clustor Computing internship, Jul 2023
    assert "● Current" in html


def test_home_shows_featured_or_first_projects(client, app):
    p = db.session.scalars(db.select(Project).order_by(Project.sort_order.desc())).first()
    p.featured = True
    db.session.commit()
    html = client.get("/").get_data(as_text=True)
    assert p.title in html and html.count('data-item') == 1


def test_custom_404_page(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404 and b"Wrong universe" in resp.data


def test_suit_up_button_links_to_login_then_dashboard(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/admin/login"' in html and "Suit Up" in html
    client.post("/admin/login", data={"username": "admin", "password": "correct-horse-battery"})
    html = client.get("/").get_data(as_text=True)
    assert 'href="/admin/"' in html and "Web HQ" in html and "Suit Up" not in html
