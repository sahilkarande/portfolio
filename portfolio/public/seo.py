"""robots.txt, sitemap.xml and search-engine verification files."""
import re

from flask import Response, abort, current_app, render_template, send_from_directory, url_for
from sqlalchemy import func, select

from ..extensions import db
from ..models import Blog, Certificate, Education, Experience, Profile, Project
from ..services.seo import site_root
from .routes import _published, bp

VERIFICATION_FILE = re.compile(r"^google[0-9a-f]{8,32}\.html$")


@bp.route("/robots.txt")
def robots():
    body = "\n".join([
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        "",
        f"Sitemap: {site_root()}{url_for('.sitemap')}",
        "",
    ])
    return Response(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    root = site_root()

    def latest(model, *where):
        return db.session.scalar(select(func.max(model.updated_at)).where(*where))

    pages = [
        (url_for(".about"), latest(Profile), "monthly", "1.0"),
        (url_for(".projects"), latest(Project, Project.is_published.is_(True)), "weekly", "0.9"),
        (url_for(".resume"), max(filter(None, [latest(Experience), latest(Education)]), default=None), "monthly", "0.8"),
        (url_for(".certificates"), latest(Certificate, Certificate.is_published.is_(True)), "monthly", "0.6"),
        (url_for(".blogs"), latest(Blog, Blog.is_published.is_(True)), "weekly", "0.6"),
        (url_for(".contact"), None, "yearly", "0.5"),
    ]
    pages += [(url_for(".project_detail", slug=p.slug), p.updated_at, "monthly", "0.7")
              for p in _published(Project)]
    xml = render_template("sitemap.xml", pages=pages, root=root)
    return Response(xml, mimetype="application/xml")


@bp.route("/<name>.html")
def verification_file(name):
    """Serve Google Search Console verification files (static/assets/google*.html) at the site root."""
    filename = f"{name}.html"
    if not VERIFICATION_FILE.match(filename):
        abort(404)
    return send_from_directory(current_app.static_folder + "/assets", filename, mimetype="text/html")

