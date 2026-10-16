import io

import pytest

from portfolio.admin.resources import RESOURCES
from portfolio.extensions import db
from portfolio.models import Category, Message, Profile, Project, SkillGroup, User

def _png(size=(2400, 1500), color=(232, 32, 42)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


PNG = _png()
PDF = b"%PDF-1.4\n" + b"\x00" * 64


def _file(data, name):
    return (io.BytesIO(data), name)


# ---------------------------------------------------------------- auth
def test_admin_requires_login(client):
    for path in ["/admin/", "/admin/projects/", "/admin/profile", "/admin/messages"]:
        resp = client.get(path)
        assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]


def test_wrong_password_then_lockout(client, app):
    for _ in range(User.MAX_FAILED_LOGINS):
        resp = client.post("/admin/login", data={"username": "admin", "password": "nope"})
        assert resp.status_code == 200
    from tests.conftest import ADMIN_PASSWORD
    resp = client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD},
                       follow_redirects=True)
    assert b"Too many failed attempts" in resp.data


def test_login_rejects_external_next(client):
    from tests.conftest import ADMIN_PASSWORD
    resp = client.post("/admin/login?next=https://evil.example/x",
                       data={"username": "admin", "password": ADMIN_PASSWORD})
    assert resp.headers["Location"] == "/admin/"


def test_logout_requires_post(admin):
    admin.get("/admin/logout", follow_redirects=True)
    assert admin.get("/admin/").status_code == 200  # a GET (e.g. a link or <img>) can't log you out
    admin.post("/admin/logout")
    assert admin.get("/admin/").status_code == 302


# ---------------------------------------------------------------- pages render
@pytest.mark.parametrize("slug", list(RESOURCES))
def test_resource_pages_render(admin, slug, app):
    assert admin.get(f"/admin/{slug}/").status_code == 200
    assert admin.get(f"/admin/{slug}/new").status_code == 200
    obj = db.session.scalars(db.select(RESOURCES[slug].model)).first()
    assert admin.get(f"/admin/{slug}/{obj.id}/edit").status_code == 200


@pytest.mark.parametrize("path", ["/admin/", "/admin/profile", "/admin/messages", "/admin/account"])
def test_admin_pages_render(admin, path):
    assert admin.get(path).status_code == 200


# ---------------------------------------------------------------- CRUD
def test_create_project_with_upload_shows_on_site(admin, app):
    cat = Category.query.filter_by(kind="project").first()
    resp = admin.post("/admin/projects/new", data={
        "title": "Spider Tracker", "summary": "Tracks spiders.", "category_id": str(cat.id),
        "status": "completed", "tech": "Python, Flask", "repo_url": "https://github.com/x/y",
        "is_published": "y", "image_upload": _file(PNG, "cover shot.png"),
    }, content_type="multipart/form-data")
    assert resp.status_code == 302
    p = Project.query.filter_by(title="Spider Tracker").one()
    assert p.slug == "spider-tracker" and p.tech == ["Python", "Flask"] and p.category == cat
    assert p.image.startswith("uploads/projects/") and p.image.endswith("cover_shot.webp")
    from PIL import Image
    stored = app.config["UPLOAD_FOLDER"] / p.image.removeprefix("uploads/")
    thumb = stored.with_name(stored.name.replace(".webp", ".thumb.webp"))
    with Image.open(stored) as im:
        assert im.format == "WEBP" and max(im.size) == 1600  # resized from 2400px
    with Image.open(thumb) as im:
        assert max(im.size) == 720
    assert p.sort_order < min(x.sort_order for x in Project.query.filter(Project.id != p.id))
    assert b"Spider Tracker" in admin.get("/projects").data


def test_fake_image_rejected(admin):
    resp = admin.post("/admin/projects/new", data={
        "title": "Bad", "summary": "x", "status": "completed",
        "image_upload": _file(b"<script>alert(1)</script>", "evil.png"),
    }, content_type="multipart/form-data")
    assert resp.status_code == 200 and b"look like a real .png" in resp.data
    assert Project.query.filter_by(title="Bad").count() == 0


def test_svg_not_allowed(admin):
    resp = admin.post("/admin/projects/new", data={
        "title": "Bad", "summary": "x", "status": "completed",
        "image_upload": _file(b"<svg/>", "x.svg"),
    }, content_type="multipart/form-data")
    assert b"aren&#39;t allowed" in resp.data or b"aren't allowed" in resp.data


def test_replacing_upload_deletes_old_file(admin, app):
    p = Project.query.first()
    admin.post(f"/admin/projects/{p.id}/edit", data={
        "title": p.title, "summary": p.summary, "status": p.status, "image": p.image,
        "image_upload": _file(PNG, "one.png")}, content_type="multipart/form-data")
    first = db.session.get(Project, p.id).image
    admin.post(f"/admin/projects/{p.id}/edit", data={
        "title": p.title, "summary": p.summary, "status": p.status, "image": first,
        "image_upload": _file(PNG, "two.png")}, content_type="multipart/form-data")
    second = db.session.get(Project, p.id).image
    root = app.config["UPLOAD_FOLDER"]
    assert second != first and (root / second.removeprefix("uploads/")).is_file()
    assert not (root / first.removeprefix("uploads/")).exists()


def test_delete_removes_upload(admin, app):
    admin.post("/admin/certificates/new", data={
        "title": "Web Slinging 101", "file_upload": _file(PDF, "cert.pdf"), "is_published": "y",
    }, content_type="multipart/form-data")
    from portfolio.models import Certificate
    c = Certificate.query.filter_by(title="Web Slinging 101").one()
    path = app.config["UPLOAD_FOLDER"] / c.file.removeprefix("uploads/")
    assert path.is_file()
    admin.post(f"/admin/certificates/{c.id}/delete")
    assert db.session.get(Certificate, c.id) is None and not path.exists()


def test_seeded_asset_files_never_deleted(admin, app):
    from pathlib import Path
    p = Project.query.first()
    original = Path(app.static_folder) / p.image
    assert original.is_file()
    admin.post(f"/admin/projects/{p.id}/delete")
    assert original.is_file()


def test_toggle_and_reorder(admin):
    p = Project.query.order_by(Project.sort_order).first()
    resp = admin.post(f"/admin/projects/{p.id}/toggle", headers={"Accept": "application/json"})
    assert resp.json == {"published": False}
    assert p.title.encode() not in admin.get("/projects").data

    ids = [x.id for x in Project.query.order_by(Project.sort_order)][::-1]
    assert admin.post("/admin/projects/reorder", json={"ids": ids}).json == {"ok": True}
    assert [x.id for x in Project.query.order_by(Project.sort_order)] == ids


def test_skill_group_edit(admin):
    g = SkillGroup.query.first()
    admin.post(f"/admin/skills/{g.id}/edit", data={"name": g.name, "skills_text": "Spark\nKafka\n\nAirflow"})
    assert [s.name for s in db.session.get(SkillGroup, g.id).skills] == ["Spark", "Kafka", "Airflow"]


def test_delete_category_unlinks_projects(admin):
    cat = Category.query.filter_by(kind="project").first()
    linked = Project.query.filter_by(category_id=cat.id).count()
    assert linked
    admin.post(f"/admin/categories/{cat.id}/delete")
    assert Project.query.filter_by(category_id=None).count() >= linked


def test_profile_update_and_resume_upload(admin, app):
    resp = admin.post("/admin/profile", data={
        "name": "Miles Morales", "headline": "Brooklyn's Spider-Man",
        "resume_upload": _file(PDF, "resume.pdf"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert b"Profile saved" in resp.data
    prof = Profile.get()
    assert prof.name == "Miles Morales" and prof.resume_file.startswith("uploads/resume/")
    page = admin.get("/resume").get_data(as_text=True)
    assert prof.resume_file in page and "Miles Morales" in page


def test_social_link_allows_mailto(admin):
    resp = admin.post("/admin/social-links/new", data={"label": "Mail", "icon": "fas fa-at", "url": "mailto:a@b.co"})
    assert resp.status_code == 302


# ---------------------------------------------------------------- messages
def test_inbox_flow(admin):
    m = Message(name="Gwen", email="gwen@example.com", body="<b>Hi</b>")
    db.session.add(m)
    db.session.commit()
    assert b"Gwen" in admin.get("/admin/messages?show=unread").data
    detail = admin.get(f"/admin/messages/{m.id}").data
    assert b"&lt;b&gt;Hi&lt;/b&gt;" in detail  # escaped
    assert db.session.get(Message, m.id).is_read
    admin.post(f"/admin/messages/{m.id}/unread")
    assert not db.session.get(Message, m.id).is_read
    admin.post(f"/admin/messages/{m.id}/delete")
    assert db.session.get(Message, m.id) is None


def test_change_password(admin):
    from tests.conftest import ADMIN_PASSWORD
    resp = admin.post("/admin/account", data={"current_password": ADMIN_PASSWORD,
                                              "new_password": "a-much-longer-pass", "confirm": "a-much-longer-pass"},
                      follow_redirects=True)
    assert b"Password updated" in resp.data
    assert User.query.one().check_password("a-much-longer-pass")


def test_avatar_becomes_jpeg_and_metadata_is_stripped(admin, app):
    from PIL import Image
    buf = io.BytesIO()
    exif = Image.Exif()
    exif[0x0110] = "Secret Camera"   # Model
    exif[0x0112] = 6                 # Orientation: rotate 90° when displayed
    Image.new("RGB", (300, 200), "white").save(buf, "JPEG", exif=exif)
    admin.post("/admin/profile", data={"name": "Sahil Karande", "avatar_upload": (io.BytesIO(buf.getvalue()), "me.jpg")},
               content_type="multipart/form-data")
    path = Profile.get().avatar
    assert path.endswith(".jpg")
    with Image.open(app.config["UPLOAD_FOLDER"] / path.removeprefix("uploads/")) as im:
        assert im.size == (200, 300)          # orientation applied
        assert not im.getexif()               # camera metadata removed


def test_corrupt_image_rejected(admin):
    resp = admin.post("/admin/projects/new", data={
        "title": "Broken", "summary": "x", "status": "completed",
        "image_upload": _file(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "broken.png"),
    }, content_type="multipart/form-data")
    assert b"Couldn" in resp.data and Project.query.filter_by(title="Broken").count() == 0


def test_delete_removes_thumbnail_too(admin, app):
    admin.post("/admin/blogs/new", data={"title": "T", "url": "https://medium.com/@x/t", "is_published": "y",
                                         "image_upload": _file(PNG, "c.png")}, content_type="multipart/form-data")
    from portfolio.models import Blog
    b = Blog.query.filter_by(title="T").one()
    folder = app.config["UPLOAD_FOLDER"] / "blogs"
    assert len(list(folder.iterdir())) == 2   # image + thumbnail
    admin.post(f"/admin/blogs/{b.id}/delete")
    assert list(folder.iterdir()) == []


def test_delete_all_messages(admin):
    db.session.add_all([Message(name=f"T{i}", email="t@example.com", body="test message") for i in range(3)])
    db.session.commit()
    assert b"Delete all" in admin.get("/admin/messages").data
    resp = admin.post("/admin/messages/delete-all", follow_redirects=True)
    assert b"Deleted 3 messages" in resp.data and Message.query.count() == 0


def test_reset_analytics(client):
    from portfolio.models import AnalyticsEvent
    client.get("/", headers={"User-Agent": "Mozilla/5.0 Chrome/130"})
    assert AnalyticsEvent.query.count() == 1
    from tests.conftest import ADMIN_PASSWORD
    client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert b"Reset analytics" in client.get("/admin/analytics").data
    resp = client.post("/admin/analytics/reset", follow_redirects=True)
    assert b"Analytics reset" in resp.data and AnalyticsEvent.query.count() == 0


def test_bulk_deletes_require_login_and_post(client):
    assert client.post("/admin/messages/delete-all").status_code == 302      # -> login
    assert client.post("/admin/analytics/reset").status_code == 302
