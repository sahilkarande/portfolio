"""Database models.

File/image columns store either a full URL (https://...) or a path relative to
the static folder (e.g. "assets/images/foo.png" or "uploads/projects/abc.png").
Use `media_url()` to turn either into something a template can use.
"""
from datetime import date, datetime, timezone

from flask import url_for
from flask_login import UserMixin
from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def media_url(path):
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    return url_for("static", filename=path)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OrderedMixin:
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class PublishableMixin:
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


# --------------------------------------------------------------------------- #
# Site profile (single row) + social links
# --------------------------------------------------------------------------- #
class Profile(TimestampMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120), default="")
    organization: Mapped[str] = mapped_column(String(160), default="")
    headline: Mapped[str] = mapped_column(String(255), default="")
    about_html: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    avatar: Mapped[str | None] = mapped_column(String(255))
    resume_file: Mapped[str | None] = mapped_column(String(255))
    years_experience: Mapped[str] = mapped_column(String(20), default="")
    education_summary: Mapped[str] = mapped_column(String(255), default="")
    expertise_summary: Mapped[str] = mapped_column(String(255), default="")
    map_label: Mapped[str] = mapped_column(String(160), default="")
    map_embed_url: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str] = mapped_column(String(300), default="")
    meta_keywords: Mapped[str] = mapped_column(String(300), default="")

    @classmethod
    def get(cls):
        return db.session.get(cls, 1) or cls(id=1, name="Your Name")


class SocialLink(OrderedMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(60))
    icon: Mapped[str] = mapped_column(String(60))  # Font Awesome class, e.g. "fab fa-github"
    url: Mapped[str] = mapped_column(String(500))


# --------------------------------------------------------------------------- #
# Projects & certificates
# --------------------------------------------------------------------------- #
class Category(OrderedMixin, db.Model):
    """Filter categories, shared by projects and certificates (see `kind`)."""
    __table_args__ = (UniqueConstraint("kind", "slug"),)

    KINDS = ("project", "certificate")

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str] = mapped_column(String(60), default="fas fa-folder")


class Project(TimestampMixin, OrderedMixin, PublishableMixin, db.Model):
    STATUSES = {"completed": "Completed", "in-progress": "In Progress", "coming-soon": "Coming Soon"}

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    summary: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str | None] = mapped_column(Text)  # long write-up for a future detail page
    image: Mapped[str | None] = mapped_column(String(255))
    tech: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    repo_url: Mapped[str | None] = mapped_column(String(500))
    live_url: Mapped[str | None] = mapped_column(String(500))
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    category: Mapped[Category | None] = relationship()

    @property
    def primary_url(self):
        return self.live_url or self.repo_url


class Certificate(TimestampMixin, OrderedMixin, PublishableMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str] = mapped_column(String(160), default="")
    image: Mapped[str | None] = mapped_column(String(255))
    file: Mapped[str | None] = mapped_column(String(255))  # uploaded PDF
    credential_url: Mapped[str | None] = mapped_column(String(500))
    issued_on: Mapped[date | None] = mapped_column(Date)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    category: Mapped[Category | None] = relationship()


# --------------------------------------------------------------------------- #
# Resume
# --------------------------------------------------------------------------- #
class Education(TimestampMixin, OrderedMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    institution: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(160), default="")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    grade: Mapped[str] = mapped_column(String(60), default="")
    courses: Mapped[list] = mapped_column(JSON, default=list)


class Experience(TimestampMixin, OrderedMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    company_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(160), default="")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    highlights: Mapped[list] = mapped_column(JSON, default=list)
    certificate: Mapped[str | None] = mapped_column(String(255))


class SkillGroup(OrderedMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(60))
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="group", order_by="Skill.sort_order", cascade="all, delete-orphan"
    )


class Skill(OrderedMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    level: Mapped[int | None] = mapped_column(Integer)  # optional 0-100, for future skill bars
    group_id: Mapped[int] = mapped_column(ForeignKey("skill_group.id"))
    group: Mapped[SkillGroup] = relationship(back_populates="skills")


# --------------------------------------------------------------------------- #
# Blogs & messages
# --------------------------------------------------------------------------- #
class Blog(TimestampMixin, OrderedMixin, PublishableMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(500), default="")
    image: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500))
    published_on: Mapped[date | None] = mapped_column(Date)


class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40), default="")
    body: Mapped[str] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


# --------------------------------------------------------------------------- #
# Admin users
# --------------------------------------------------------------------------- #
class User(UserMixin, db.Model):
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > utcnow())

    def register_failed_login(self):
        from datetime import timedelta
        self.failed_logins = (self.failed_logins or 0) + 1
        if self.failed_logins >= self.MAX_FAILED_LOGINS:
            self.locked_until = utcnow() + timedelta(minutes=self.LOCKOUT_MINUTES)
            self.failed_logins = 0

    def register_successful_login(self):
        self.failed_logins = 0
        self.locked_until = None
        self.last_login_at = utcnow()


# --------------------------------------------------------------------------- #
# Privacy-friendly analytics (no cookies, no raw IPs, visitor id rotates daily)
# --------------------------------------------------------------------------- #
class AnalyticsEvent(db.Model):
    __table_args__ = (db.Index("ix_analytics_kind_created", "kind", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))            # "view" or "click"
    path: Mapped[str] = mapped_column(String(255))
    endpoint: Mapped[str | None] = mapped_column(String(80))
    target: Mapped[str | None] = mapped_column(String(220))  # project slug (views) / click label
    action: Mapped[str | None] = mapped_column(String(20))   # click type: repo, live, resume, social, email
    referrer: Mapped[str | None] = mapped_column(String(160))  # external referring host only
    visitor: Mapped[str] = mapped_column(String(16), index=True)
    device: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
