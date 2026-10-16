import logging
import os
from urllib.parse import urlsplit

from flask import Flask, flash, redirect, render_template, request
from flask_wtf.csrf import CSRFError
from sqlalchemy import func, select

from . import commands
from .config import BASE_DIR, CONFIGS
from .extensions import csrf, db, login_manager, migrate
from .services.content import render_markdown
from .services.media import thumb_url_path
from .services.seo import site_root
from .models import (Blog, Certificate, Education, Experience, Profile, Project, SocialLink, media_url,
                     utcnow)


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV_NAME", "production")

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        instance_path=str(BASE_DIR / "instance"),
    )
    app.config.from_object(CONFIGS[config_name])
    app.json.sort_keys = False  # keep admin-defined order (e.g. skill groups) in |tojson
    os.makedirs(app.instance_path, exist_ok=True)

    if config_name == "production" and app.config["SECRET_KEY"] == "dev-only-change-me":
        raise RuntimeError("Set SECRET_KEY in .env before running in production.")

    if config_name == "production":
        # PythonAnywhere terminates HTTPS at its proxy; trust its forwarded scheme/host.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)  # batch mode lets SQLite handle ALTERs
    csrf.init_app(app)
    login_manager.init_app(app)

    from .public import bp as public_bp
    app.register_blueprint(public_bp)
    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    commands.register(app)
    _register_template_helpers(app)
    _register_error_handlers(app)
    logging.basicConfig(level=logging.INFO)
    return app


def _register_template_helpers(app):
    app.jinja_env.globals["media_url"] = media_url
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.globals["thumb_url"] = lambda path: media_url(thumb_url_path(path))

    @app.template_filter("duration")
    def duration(start, end=None):
        """'1 yr 3 mos' between two dates (end defaults to today)."""
        if not start:
            return ""
        end = end or utcnow().date()
        months = max((end.year - start.year) * 12 + end.month - start.month + (end.day >= start.day), 1)
        years, months = divmod(months, 12)
        parts = [f"{years} yr{'s' if years > 1 else ''}"] if years else []
        if months:
            parts.append(f"{months} mo{'s' if months > 1 else ''}")
        return " ".join(parts)

    @app.template_filter("site_name")
    def site_name(url):
        """'Medium' for https://medium.com/@me/post — used for 'Read on …' links."""
        host = urlsplit(url or "").netloc.lower().removeprefix("www.")
        return {"medium.com": "Medium", "dev.to": "DEV", "hashnode.com": "Hashnode",
                "linkedin.com": "LinkedIn", "substack.com": "Substack"}.get(
            ".".join(host.split(".")[-2:]), host or "the web")

    @app.context_processor
    def site_context():
        last_updated = max(
            (d for d in (db.session.scalar(select(func.max(m.updated_at)))
                         for m in (Profile, Project, Certificate, Education, Experience, Blog)) if d),
            default=None,
        )
        profile = Profile.get()
        return {
            "profile": profile,
            "initials": "".join(w[0] for w in (profile.name or "?").split()[:2]).upper(),
            "now_year": utcnow().year,
            "site_root": site_root(),
            "social_links": db.session.scalars(select(SocialLink).order_by(SocialLink.sort_order)).all(),
            "site_updated": last_updated,
        }


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", title="404 - Not Found"), 404

    @app.errorhandler(413)
    def too_large(e):
        flash("That file is too large (max 16 MB).", "error")
        return redirect(request.referrer or "/")

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        flash("Your session expired. Please try again.", "error")
        return redirect(request.referrer or "/")

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("404.html", title="Something went wrong", code=500), 500
