from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from ..extensions import csrf, db
from ..models import (Blog, Category, Certificate, Education, Experience, Message, Profile,
                      Project, SkillGroup, SocialLink, utcnow)
from ..services import analytics
from ..services import seo as schema
from ..services.mailer import send_contact_emails
from .forms import ContactForm

bp = Blueprint("public", __name__)

TRACKED_ENDPOINTS = {"public.about", "public.projects", "public.project_detail", "public.resume",
                     "public.certificates", "public.blogs", "public.contact"}


@bp.after_request
def track_page_view(response):
    if request.endpoint in TRACKED_ENDPOINTS:
        analytics.record_view(response)
    return response


@bp.route("/t", methods=["POST"])
@csrf.exempt
def track_click():
    """Beacon endpoint for outbound clicks (sent by navigator.sendBeacon)."""
    data = request.get_json(silent=True, force=True) or {}
    analytics.record_click(str(data.get("e", ""))[:20], str(data.get("l", ""))[:80], data.get("p"))
    return "", 204

MAX_MESSAGES_PER_WINDOW = 3
RATE_WINDOW = timedelta(minutes=10)


def _published(model):
    return db.session.scalars(
        select(model).where(model.is_published.is_(True)).order_by(model.sort_order, model.id)
    ).all()


def _ordered(model):
    return db.session.scalars(select(model).order_by(model.sort_order, model.id)).all()


def _categories(kind):
    return db.session.scalars(
        select(Category).where(Category.kind == kind).order_by(Category.sort_order, Category.id)
    ).all()


def _client_ip():
    # PythonAnywhere puts the real client address in X-Real-IP.
    return request.headers.get("X-Real-IP") or request.remote_addr


@bp.route("/")
def about():
    projects = _published(Project)
    featured = [p for p in projects if p.featured][:3] or projects[:3]
    experience = _ordered(Experience)
    current_role = next((e for e in experience if e.current), experience[0] if experience else None)
    skills = [s.name for g in _ordered(SkillGroup) for s in g.skills]
    stats = {
        "projects": len(projects),
        "certificates": db.session.scalar(
            select(func.count(Certificate.id)).where(Certificate.is_published.is_(True))),
        "skills": len(skills),
    }
    root = schema.site_root()
    profile = Profile.get()
    structured = [schema.person(profile, _ordered(SocialLink), _ordered(Education), skills, root),
                  schema.website(profile, root)]
    return render_template("home.html", title="Home", stats=stats, featured=featured,
                           current_role=current_role, skills=skills, structured_data=structured)


@bp.route("/resume")
def resume():
    return render_template("resume.html", title="Resume", experience=_ordered(Experience),
                           education=_ordered(Education), skill_groups=_ordered(SkillGroup))


@bp.route("/projects")
def projects():
    return render_template("projects.html", title="Projects", projects=_published(Project),
                           categories=_categories("project"))


@bp.route("/projects/<slug>")
def project_detail(slug):
    project = db.session.scalar(select(Project).where(Project.slug == slug)) or abort(404)
    is_preview = not project.is_published
    if is_preview and not current_user.is_authenticated:  # admins can preview hidden projects
        abort(404)
    published = _published(Project)
    index = next((i for i, p in enumerate(published) if p.id == project.id), None)
    prev_p = published[index - 1] if index else None
    next_p = published[index + 1] if index is not None and index + 1 < len(published) else None
    root = schema.site_root()
    related = [p for p in published if p.id != project.id and project.category_id
               and p.category_id == project.category_id][:3]
    return render_template("project_detail.html", title=project.title, project=project,
                           prev_project=prev_p, next_project=next_p, related=related,
                           is_preview=is_preview, number=(index or 0) + 1,
                           og_image=project.image, og_type="article",
                           structured_data=schema.project(
                               project, Profile.get(), root + url_for(".project_detail", slug=slug),
                               root, root + url_for(".projects")))


@bp.route("/certificates")
def certificates():
    return render_template("certificates.html", title="Certificates",
                           certificates=_published(Certificate), categories=_categories("certificate"))


@bp.route("/blogs")
def blogs():
    return render_template("blogs.html", title="Blogs", blogs=_published(Blog))


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        if form.website.data:  # honeypot tripped: pretend success, store nothing
            flash("Message sent successfully!", "success")
            return redirect(url_for(".contact"))

        ip = _client_ip()
        recent = db.session.scalar(
            select(func.count(Message.id)).where(
                Message.ip_address == ip, Message.created_at >= utcnow() - RATE_WINDOW)
        )
        if recent >= MAX_MESSAGES_PER_WINDOW:
            flash("You've sent several messages recently. Please try again in a few minutes.", "error")
            return redirect(url_for(".contact"))

        message = Message(
            name=form.fullname.data.strip(),
            email=form.email.data.strip(),
            phone=(form.phone.data or "").strip(),
            body=form.message.data.strip(),
            ip_address=ip,
        )
        db.session.add(message)
        db.session.commit()  # saved first, so nothing is lost if email fails

        message.email_sent = send_contact_emails(message, Profile.get())
        db.session.commit()
        flash("Message sent successfully! I'll get back to you soon.", "success")
        return redirect(url_for(".contact"))

    if request.method == "POST":
        flash("Please check the form: " + "; ".join(
            f"{form[name].label.text}: {errs[0]}" for name, errs in form.errors.items()), "error")
    return render_template("contact.html", title="Contact", form=form)
