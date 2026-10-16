from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, inspect, select
from wtforms import FileField

from ..extensions import db, login_manager
from ..models import Blog, Certificate, Experience, Message, Profile, Project, SkillGroup, User
from ..services.media import DOCUMENTS, IMAGES, UploadError, delete_upload, file_exists, save_upload
from .forms import LoginForm, PasswordForm, ProfileForm
from .resources import NAV_GROUPS, RESOURCES

bp = Blueprint("admin", __name__, url_prefix="/admin")

PROFILE_UPLOADS = {"avatar_upload": ("avatar", "profile", IMAGES),
                   "resume_upload": ("resume_file", "resume", DOCUMENTS)}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@bp.before_request
def require_login():
    if request.endpoint not in ("admin.login",) and not current_user.is_authenticated:
        return login_manager.unauthorized()


@bp.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@bp.context_processor
def admin_context():
    return {
        "resources": RESOURCES,
        "nav_groups": NAV_GROUPS,
        "unread_count": db.session.scalar(select(func.count(Message.id)).where(Message.is_read.is_(False))),
    }


def _safe_next(target):
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for(".dashboard")


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(".dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == form.username.data.strip()))
        if user and user.is_locked:
            flash("Too many failed attempts. Try again in a few minutes.", "error")
        elif user and user.check_password(form.password.data):
            user.register_successful_login()
            db.session.commit()
            login_user(user, remember=form.remember.data)
            return redirect(_safe_next(request.args.get("next")))
        else:
            if user:
                user.register_failed_login()
                db.session.commit()
            flash("Invalid username or password.", "error")
    return render_template("admin/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for(".login"))


@bp.route("/account", methods=["GET", "POST"])
def account():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("That's not your current password.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for(".account"))
    return render_template("admin/account.html", form=form)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def _missing_files():
    """Content rows that point at files which don't exist."""
    missing = []
    for res in RESOURCES.values():
        attrs = [a for a, _, _ in res.uploads.values()]
        for obj in db.session.scalars(select(res.model)).all() if attrs else []:
            for attr in attrs:
                path = getattr(obj, attr)
                if not file_exists(path):
                    missing.append({"resource": res, "obj": obj, "attr": attr, "path": path})
    profile = Profile.get()
    for attr in ("avatar", "resume_file"):
        if not file_exists(getattr(profile, attr)):
            missing.append({"resource": None, "obj": profile, "attr": attr, "path": getattr(profile, attr)})
    return missing


@bp.route("/")
def dashboard():
    count = lambda model, *where: db.session.scalar(select(func.count(model.id)).where(*where))  # noqa: E731
    stats = [
        ("projects", "Projects", count(Project), count(Project, Project.is_published.is_(False))),
        ("certificates", "Certificates", count(Certificate), count(Certificate, Certificate.is_published.is_(False))),
        ("blogs", "Blogs", count(Blog), count(Blog, Blog.is_published.is_(False))),
        ("experience", "Experience", count(Experience), 0),
        ("skills", "Skill groups", count(SkillGroup), 0),
    ]
    recent = db.session.scalars(select(Message).order_by(Message.created_at.desc()).limit(5)).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent,
                           total_messages=count(Message), missing=_missing_files())


# --------------------------------------------------------------------------- #
# Generic content management
# --------------------------------------------------------------------------- #
def _resource(slug):
    return RESOURCES.get(slug) or abort(404)


def _get(res, obj_id):
    return db.session.get(res.model, obj_id) or abort(404)


def _populate(form, obj, skip, model):
    """Copy form data onto the model; blank strings become NULL for nullable columns."""
    columns = {c.key: c for c in inspect(model).columns}
    for name, fld in form._fields.items():
        if name in skip or isinstance(fld, FileField) or not hasattr(model, name):
            continue
        value = fld.data
        if isinstance(value, str):
            value = value.strip()
            if value == "" and name in columns and columns[name].nullable:
                value = None
        setattr(obj, name, value)


def _handle_uploads(form, obj, uploads):
    """Save uploaded files onto obj. Returns False (with form errors set) on invalid files."""
    saved, ok = [], True
    for field_name, (attr, kind, allowed) in uploads.items():
        try:
            path = save_upload(form[field_name].data, kind, allowed)
        except UploadError as e:
            form[field_name].errors = [str(e)]
            ok = False
            continue
        if path:
            saved.append(path)
            setattr(obj, attr, path)
    if not ok:  # don't leave orphaned files behind when the form is rejected
        for path in saved:
            delete_upload(path)
    return ok


def _cleanup_replaced(old_paths, obj, uploads):
    for attr, _, _ in uploads.values():
        old = old_paths.get(attr)
        if old and old != getattr(obj, attr):
            delete_upload(old)


def _save_form(res, form, obj, is_new):
    old_paths = {attr: getattr(obj, attr) for attr, _, _ in res.uploads.values()}
    _populate(form, obj, res.form_skip, res.model)
    if not _handle_uploads(form, obj, res.uploads):
        db.session.rollback()
        return False
    if res.before_save:
        res.before_save(form, obj)
    if is_new:
        if res.sortable:  # new items go to the top
            lowest = db.session.scalar(select(func.min(res.model.sort_order)))
            obj.sort_order = (lowest or 0) - 1
        db.session.add(obj)
    db.session.commit()
    _cleanup_replaced(old_paths, obj, res.uploads)
    return True


@bp.route("/<res_slug>/")
def resource_list(res_slug):
    res = _resource(res_slug)
    order = [res.model.sort_order, res.model.id] if res.sortable else [res.model.id]
    items = db.session.scalars(select(res.model).order_by(*order)).all()
    return render_template("admin/list.html", res=res, items=items)


@bp.route("/<res_slug>/new", methods=["GET", "POST"])
@bp.route("/<res_slug>/<int:obj_id>/edit", methods=["GET", "POST"])
def resource_edit(res_slug, obj_id=None):
    res = _resource(res_slug)
    obj = _get(res, obj_id) if obj_id else None
    form = res.form(obj=obj)
    form._obj_id = obj_id
    if res.prepare_form:
        res.prepare_form(form)
    if obj is not None and request.method == "GET" and res.load_form:
        res.load_form(form, obj)

    if form.validate_on_submit():
        target = obj or res.model()
        if _save_form(res, form, target, is_new=obj is None):
            flash(f"{res.singular} “{_title(target)}” saved.", "success")
            if request.form.get("action") == "save_add":
                return redirect(url_for(".resource_edit", res_slug=res.slug))
            return redirect(url_for(".resource_list", res_slug=res.slug))
    elif request.method == "POST":
        flash("Please fix the highlighted fields.", "error")
    return render_template("admin/form.html", res=res, form=form, obj=obj)


@bp.route("/<res_slug>/<int:obj_id>/delete", methods=["POST"])
def resource_delete(res_slug, obj_id):
    res = _resource(res_slug)
    obj = _get(res, obj_id)
    files, title = res.files_of(obj), _title(obj)
    if res.before_delete:
        res.before_delete(obj)
    db.session.delete(obj)
    db.session.commit()
    for path in files:
        delete_upload(path)
    flash(f"Deleted “{title}”.", "success")
    return redirect(url_for(".resource_list", res_slug=res.slug))


@bp.route("/<res_slug>/<int:obj_id>/toggle", methods=["POST"])
def resource_toggle(res_slug, obj_id):
    res = _resource(res_slug)
    if not res.publishable:
        abort(400)
    obj = _get(res, obj_id)
    obj.is_published = not obj.is_published
    db.session.commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(published=obj.is_published)
    flash(f"“{_title(obj)}” is now {'visible' if obj.is_published else 'hidden'}.", "success")
    return redirect(url_for(".resource_list", res_slug=res.slug))


@bp.route("/<res_slug>/reorder", methods=["POST"])
def resource_reorder(res_slug):
    res = _resource(res_slug)
    if not res.sortable:
        abort(400)
    ids = (request.get_json(silent=True) or {}).get("ids", [])
    objs = {o.id: o for o in db.session.scalars(select(res.model).where(res.model.id.in_(ids)))}
    for position, obj_id in enumerate(ids):
        if obj := objs.get(int(obj_id)):
            obj.sort_order = position
    db.session.commit()
    return jsonify(ok=True)


def _title(obj):
    return getattr(obj, "title", None) or getattr(obj, "name", None) or getattr(obj, "label", None) or f"#{obj.id}"


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #
@bp.route("/profile", methods=["GET", "POST"])
def profile():
    obj = Profile.get()
    form = ProfileForm(obj=obj)
    if form.validate_on_submit():
        old_paths = {attr: getattr(obj, attr) for attr, _, _ in PROFILE_UPLOADS.values()}
        _populate(form, obj, set(PROFILE_UPLOADS), Profile)
        if _handle_uploads(form, obj, PROFILE_UPLOADS):
            db.session.add(obj)
            db.session.commit()
            _cleanup_replaced(old_paths, obj, PROFILE_UPLOADS)
            flash("Profile saved.", "success")
            return redirect(url_for(".profile"))
        db.session.rollback()
    elif request.method == "POST":
        flash("Please fix the highlighted fields.", "error")
    return render_template("admin/profile.html", form=form, obj=obj, uploads=PROFILE_UPLOADS)


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #
@bp.route("/messages")
def messages():
    show = request.args.get("show", "all")
    query = select(Message).order_by(Message.created_at.desc())
    if show == "unread":
        query = query.where(Message.is_read.is_(False))
    page = db.paginate(query, per_page=25, error_out=False)
    return render_template("admin/messages.html", page=page, show=show)


@bp.route("/messages/<int:msg_id>")
def message_detail(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    if not msg.is_read:
        msg.is_read = True
        db.session.commit()
    return render_template("admin/message.html", msg=msg)


@bp.route("/messages/<int:msg_id>/unread", methods=["POST"])
def message_unread(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    msg.is_read = False
    db.session.commit()
    return redirect(url_for(".messages"))


@bp.route("/messages/<int:msg_id>/delete", methods=["POST"])
def message_delete(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted.", "success")
    return redirect(url_for(".messages"))


@bp.route("/messages/mark-all-read", methods=["POST"])
def messages_mark_all_read():
    db.session.query(Message).filter(Message.is_read.is_(False)).update({"is_read": True})
    db.session.commit()
    return redirect(url_for(".messages"))


@bp.app_template_filter("format_ext")
def format_ext(ext):
    return f".{ext}"


@bp.app_template_filter("capitalize_first")
def capitalize_first(row):
    return [str(row[0]).capitalize(), *row[1:]]
