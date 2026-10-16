import json
import re

from portfolio.extensions import db
from portfolio.models import AnalyticsEvent, Project

BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def _views():
    return db.session.scalar(db.select(db.func.count(AnalyticsEvent.id)).where(AnalyticsEvent.kind == "view"))


# ---------------------------------------------------------------- project detail pages
def test_project_detail_page(client):
    p = db.session.scalars(db.select(Project).order_by(Project.sort_order)).first()
    p.body = "## The problem\n\nSome **bold** text.\n\n<script>alert(1)</script>\n\n[link](https://example.com)"
    db.session.commit()
    html = client.get(f"/projects/{p.slug}").get_data(as_text=True)
    assert p.title in html and "<h2>The problem</h2>" in html and "<strong>bold</strong>" in html
    assert "<script>alert(1)</script>" not in html                     # raw HTML in markdown is sanitised
    assert 'rel="noopener noreferrer"' in html
    assert f'href="/projects/{p.slug}"' in client.get("/projects").get_data(as_text=True)  # cards link here


def test_hidden_project_404_for_visitors_but_previewable_by_admin(client, admin):
    p = db.session.scalars(db.select(Project)).first()
    p.is_published = False
    db.session.commit()
    assert admin.get(f"/projects/{p.slug}").status_code == 200       # admin preview
    admin.post("/admin/logout")
    assert client.get(f"/projects/{p.slug}").status_code == 404
    assert client.get("/projects/does-not-exist").status_code == 404


def test_project_pager_and_related(client):
    projects = db.session.scalars(db.select(Project).order_by(Project.sort_order)).all()
    from html import unescape
    html = unescape(client.get(f"/projects/{projects[1].slug}").get_data(as_text=True))
    assert projects[0].title in html and projects[2].title in html  # previous / next


# ---------------------------------------------------------------- SEO
def test_robots_and_sitemap(client):
    robots = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin/" in robots and "Sitemap: http://localhost/sitemap.xml" in robots
    resp = client.get("/sitemap.xml")
    assert resp.mimetype == "application/xml"
    xml = resp.get_data(as_text=True)
    published = db.session.scalars(db.select(Project).where(Project.is_published.is_(True))).all()
    assert all(f"/projects/{p.slug}</loc>" in xml for p in published)
    assert "/admin" not in xml


def test_structured_data_on_home(client):
    html = client.get("/").get_data(as_text=True)
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    person = next(b for b in blocks if b["@type"] == "Person")
    assert person["name"] == "Sahil Karande" and person["jobTitle"]
    assert any("github.com" in url for url in person["sameAs"])
    assert '<link rel="canonical" href="http://localhost/">' in html


def test_structured_data_on_project(client):
    p = db.session.scalars(db.select(Project).where(Project.repo_url.is_not(None))).first()
    html = client.get(f"/projects/{p.slug}").get_data(as_text=True)
    types = re.findall(r'"@type": ?"(\w+)"', html)
    assert "SoftwareSourceCode" in types and "BreadcrumbList" in types


def test_google_verification_file_served_at_root(client):
    resp = client.get("/googlec2d288ffdefa9086.html")
    assert resp.status_code == 200 and b"google-site-verification" in resp.data
    assert client.get("/secret.html").status_code == 404


# ---------------------------------------------------------------- analytics
def test_page_views_recorded_for_real_browsers_only(client):
    client.get("/", headers=BROWSER)
    client.get("/projects", headers=BROWSER)
    assert _views() == 2
    client.get("/", headers={"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"})
    client.get("/", headers={**BROWSER, "DNT": "1"})
    client.get("/", headers={**BROWSER, "Sec-GPC": "1"})
    client.get("/static/css/site.css", headers=BROWSER)
    client.get("/nope", headers=BROWSER)
    assert _views() == 2
    event = db.session.scalars(db.select(AnalyticsEvent)).first()
    assert len(event.visitor) == 16 and "127.0.0.1" not in event.visitor  # hashed, no raw IP


def test_admin_visits_not_counted(admin):
    admin.get("/", headers=BROWSER)
    assert _views() == 0


def test_external_referrer_and_project_target(client):
    p = db.session.scalars(db.select(Project)).first()
    client.get(f"/projects/{p.slug}", headers={**BROWSER, "Referer": "https://www.linkedin.com/feed/"})
    client.get("/", headers={**BROWSER, "Referer": "http://localhost/projects"})
    events = db.session.scalars(db.select(AnalyticsEvent).order_by(AnalyticsEvent.id)).all()
    assert events[0].referrer == "linkedin.com" and events[0].target == p.slug
    assert events[1].referrer is None  # internal navigation isn't a referrer


def test_click_beacon(client):
    assert client.post("/t", json={"e": "repo", "l": "therapy-connect", "p": "/projects/x"}, headers=BROWSER).status_code == 204
    client.post("/t", json={"e": "evil", "l": "x"}, headers=BROWSER)              # unknown action ignored
    client.post("/t", json={"e": "social", "l": "<script>"}, headers=BROWSER)     # bad label dropped
    clicks = db.session.scalars(db.select(AnalyticsEvent).where(AnalyticsEvent.kind == "click")).all()
    assert [(c.action, c.target) for c in clicks] == [("repo", "therapy-connect"), ("social", None)]


def test_analytics_report_renders_with_data(client):
    p = db.session.scalars(db.select(Project)).first()
    for _ in range(3):
        client.get(f"/projects/{p.slug}", headers={**BROWSER, "Referer": "https://github.com/"})
    client.post("/t", json={"e": "resume", "p": "/"}, headers=BROWSER)
    client.post("/admin/login", data={"username": "admin", "password": "correct-horse-battery"})
    for days in (7, 30, 90):
        html = client.get(f"/admin/analytics?days={days}").get_data(as_text=True)
        assert p.title in html and "github.com" in html and "Resume downloads" in html


def test_analytics_report_empty(admin):
    assert b"start recording" in admin.get("/admin/analytics").data
