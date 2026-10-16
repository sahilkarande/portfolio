"""First-party, privacy-friendly analytics.

- No cookies and no raw IP addresses are stored.
- A visitor is a hash of (secret, day, IP, user agent): it changes every day, so
  visitors can be counted per day but never followed over time.
- Bots, the logged-in admin, and browsers sending Do-Not-Track / Global Privacy
  Control are not recorded.
"""
import hashlib
import logging
import re
from datetime import timedelta
from urllib.parse import urlsplit

from flask import current_app, request
from flask_login import current_user

from ..extensions import db
from ..models import AnalyticsEvent, utcnow

log = logging.getLogger(__name__)

BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|curl|wget|python-|"
                    r"httpclient|headless|lighthouse|pingdom|uptime|monitor|scrapy|okhttp|go-http", re.I)
CLICK_ACTIONS = {"repo", "live", "resume", "social", "email"}
LABEL_RE = re.compile(r"^[\w .@+-]{1,80}$")
CLICKS_PER_VISITOR_PER_HOUR = 120


def _client_ip():
    # PythonAnywhere's proxy sends the real address in X-Real-IP; ProxyFix covers remote_addr.
    return request.headers.get("X-Real-IP") or request.remote_addr


def should_track():
    if not current_app.config.get("ANALYTICS_ENABLED", True):
        return False
    if current_user.is_authenticated:  # don't count yourself
        return False
    if request.headers.get("DNT") == "1" or request.headers.get("Sec-GPC") == "1":
        return False
    ua = request.user_agent.string or ""
    return bool(ua) and not BOT_RE.search(ua)


def visitor_id():
    raw = f"{current_app.config['SECRET_KEY']}|{utcnow().date()}|{_client_ip()}|{request.user_agent.string}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def device():
    ua = request.user_agent.string or ""
    if re.search(r"iPad|Tablet|PlayBook|Silk|(Android(?!.*Mobile))", ua):
        return "tablet"
    if re.search(r"Mobi|iPhone|Android", ua):
        return "mobile"
    return "desktop"


def external_referrer():
    host = urlsplit(request.referrer or "").netloc.lower().removeprefix("www.")
    own = request.host.lower().removeprefix("www.")
    return host[:160] if host and host != own else None


def _save(event):
    try:
        db.session.add(event)
        db.session.commit()
    except Exception:  # analytics must never break a page
        db.session.rollback()
        log.exception("Failed to record analytics event")


def record_view(response):
    if (request.method != "GET" or response.status_code != 200
            or response.mimetype != "text/html" or not should_track()):
        return
    target = request.view_args.get("slug") if request.view_args else None
    _save(AnalyticsEvent(kind="view", path=request.path[:255], endpoint=request.endpoint, target=target,
                         referrer=external_referrer(), visitor=visitor_id(), device=device()))


def record_click(action, label, path):
    """Returns True if recorded."""
    if action not in CLICK_ACTIONS or not should_track():
        return False
    label = label if label and LABEL_RE.match(label) else None
    visitor = visitor_id()
    recent = db.session.query(AnalyticsEvent).filter(
        AnalyticsEvent.visitor == visitor, AnalyticsEvent.kind == "click",
        AnalyticsEvent.created_at >= utcnow() - timedelta(hours=1)).count()
    if recent >= CLICKS_PER_VISITOR_PER_HOUR:
        return False
    path = path if isinstance(path, str) and path.startswith("/") else "/"
    _save(AnalyticsEvent(kind="click", path=path[:255], action=action, target=label,
                         visitor=visitor, device=device()))
    return True


def prune(days):
    cutoff = utcnow() - timedelta(days=days)
    deleted = db.session.query(AnalyticsEvent).filter(AnalyticsEvent.created_at < cutoff).delete()
    db.session.commit()
    return deleted
