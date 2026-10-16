"""Admin analytics report (works on SQLite and MySQL)."""
import math
from datetime import timedelta

from flask import current_app, render_template, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import AnalyticsEvent as E
from ..models import Project, utcnow
from ..services import analytics
from .routes import bp

RANGES = (7, 30, 90)
PAGE_NAMES = {"/": "Home", "/projects": "Projects", "/resume": "Resume", "/certificates": "Certificates",
              "/blogs": "Blogs", "/contact": "Contact"}
ACTION_NAMES = {"resume": "Resume downloads", "repo": "GitHub / source", "live": "Live demos",
                "social": "Social profiles", "email": "Email links"}


def _count(*where, distinct=None):
    col = func.count(func.distinct(distinct)) if distinct is not None else func.count(E.id)
    return db.session.scalar(select(col).where(*where)) or 0


def _grouped(column, *where, limit=8):
    rows = db.session.execute(
        select(column, func.count(E.id).label("n")).where(*where).group_by(column)
        .order_by(func.count(E.id).desc()).limit(limit)).all()
    return [(key, n) for key, n in rows if key]


def _delta(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100)


def _nice_step(value, steps=4):
    """Clean tick step (1/2/5 × 10^k) so that steps × step >= value."""
    raw = max(value / steps, 1)
    exp = 10 ** math.floor(math.log10(raw))
    return next(m * exp for m in (1, 2, 5, 10) if raw <= m * exp)


def _chart(days, start):
    """Daily views + visitors, with column geometry precomputed for an inline SVG."""
    day = func.date(E.created_at)
    views = dict(db.session.execute(select(day, func.count(E.id)).where(
        E.kind == "view", E.created_at >= start).group_by(day)).all())
    visitors = dict(db.session.execute(select(day, func.count(func.distinct(E.visitor))).where(
        E.kind == "view", E.created_at >= start).group_by(day)).all())
    views = {str(k)[:10]: v for k, v in views.items()}
    visitors = {str(k)[:10]: v for k, v in visitors.items()}

    series = []
    for i in range(days):
        d = (start + timedelta(days=i)).date()
        series.append({"date": d, "views": views.get(d.isoformat(), 0), "visitors": visitors.get(d.isoformat(), 0)})

    width, height, left, bottom, top = 720, 220, 36, 26, 10
    plot_w, plot_h = width - left - 8, height - bottom - top
    step = _nice_step(max((s["views"] for s in series), default=0))
    y_max = step * 4
    slot = plot_w / days
    bar_w = min(24, max(slot - 2, 2))  # ≤24px, ≥2px surface gap between columns
    for i, s in enumerate(series):
        h = s["views"] / y_max * plot_h
        x = left + i * slot + (slot - bar_w) / 2
        r = min(4, h, bar_w / 2)
        y = top + plot_h - h
        base = top + plot_h
        s["path"] = (f"M{x:.1f},{base:.1f}V{y + r:.1f}Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}"
                     f"H{x + bar_w - r:.1f}Q{x + bar_w:.1f},{y:.1f} {x + bar_w:.1f},{y + r:.1f}V{base:.1f}Z"
                     if h > 0 else "")
        s["hit_x"], s["hit_w"] = left + i * slot, slot
    ticks = [{"value": step * k, "y": top + plot_h - plot_h * k / 4} for k in range(5)]
    label_idx = sorted({0, days // 2, days - 1})
    return {"series": series, "ticks": ticks, "width": width, "height": height, "left": left,
            "top": top, "plot_h": plot_h, "plot_w": plot_w, "labels": [(series[i], left + (i + .5) * slot) for i in label_idx]}


@bp.route("/analytics")
def analytics_report():
    days = request.args.get("days", 30, type=int)
    days = days if days in RANGES else 30
    analytics.prune(current_app.config["ANALYTICS_RETENTION_DAYS"])

    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    prev_start = start - timedelta(days=days)
    in_range = (E.created_at >= start,)
    in_prev = (E.created_at >= prev_start, E.created_at < start)
    view, click = E.kind == "view", E.kind == "click"

    kpis = []
    for label, where, distinct in (("Page views", view, None), ("Visitors", view, E.visitor),
                                    ("Outbound clicks", click, None)):
        now_n, prev_n = _count(where, *in_range, distinct=distinct), _count(where, *in_prev, distinct=distinct)
        kpis.append({"label": label, "value": now_n, "delta": _delta(now_n, prev_n)})
    views_n, visitors_n = kpis[0]["value"], kpis[1]["value"]
    kpis.append({"label": "Pages per visitor", "value": f"{views_n / visitors_n:.1f}" if visitors_n else "—",
                 "delta": None})

    titles = {p.slug: p.title for p in db.session.scalars(select(Project))}
    project_views = dict(_grouped(E.target, view, E.endpoint == "public.project_detail", *in_range, limit=50))
    project_clicks = dict(_grouped(E.target, click, E.action.in_(("repo", "live")), *in_range, limit=50))
    top_projects = sorted(
        ({"title": titles.get(slug, slug), "slug": slug, "views": project_views.get(slug, 0),
          "clicks": project_clicks.get(slug, 0)} for slug in set(project_views) | set(project_clicks)),
        key=lambda r: (r["views"], r["clicks"]), reverse=True)[:8]

    pages = [(PAGE_NAMES.get(path, titles.get(path.rsplit("/", 1)[-1], path)), path, n)
             for path, n in _grouped(E.path, view, *in_range)]

    return render_template(
        "admin/analytics.html", days=days, ranges=RANGES, kpis=kpis, chart=_chart(days, start),
        pages=pages, top_projects=top_projects,
        referrers=_grouped(E.referrer, view, *in_range),
        devices=_grouped(E.device, view, *in_range),
        clicks=[(ACTION_NAMES.get(a, a), n) for a, n in _grouped(E.action, click, *in_range)],
        total_events=_count(),
    )
