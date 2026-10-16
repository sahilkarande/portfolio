"""Declarative description of every content type the admin can manage.

Adding a new content type = add a model, a form, and one Resource entry here.
"""
from dataclasses import dataclass, field
from typing import Callable

from flask import url_for
from slugify import slugify

from ..models import (Blog, Category, Certificate, Education, Experience, Project, Skill, SkillGroup,
                      SocialLink)
from ..services.media import DOCUMENTS, IMAGES
from . import forms


def _date_range(obj):
    fmt = lambda d: d.strftime("%b %Y") if d else "?"  # noqa: E731
    return f"{fmt(obj.start_date)} – {'Present' if obj.current else fmt(obj.end_date)}"


@dataclass
class Resource:
    slug: str
    model: type
    form: type
    label: str
    singular: str
    icon: str
    columns: list[tuple[str, Callable]]
    # upload field name -> (model attribute, upload sub-folder, allowed extensions)
    uploads: dict[str, tuple[str, str, set]] = field(default_factory=dict)
    thumbnail: str | None = None
    description: str = ""
    # hooks
    prepare_form: Callable | None = None   # (form) -> None, before validation/render
    load_form: Callable | None = None      # (form, obj) -> None, prefill extra fields on edit
    before_save: Callable | None = None    # (form, obj) -> None, after populate, before commit
    before_delete: Callable | None = None  # (obj) -> None
    public_url: Callable | None = None     # (obj) -> URL of the item on the public site

    @property
    def sortable(self):
        return hasattr(self.model, "sort_order")

    @property
    def publishable(self):
        return hasattr(self.model, "is_published")

    @property
    def form_skip(self):
        """Form fields that aren't plain model attributes."""
        return set(self.uploads) | {"csrf_token"}

    def files_of(self, obj):
        return [getattr(obj, attr) for attr, _, _ in self.uploads.values()]


# --------------------------------------------------------------------------- #
# Hooks
# --------------------------------------------------------------------------- #
def _unique_slug(model, base, obj_id):
    slug, n = base, 2
    while (existing := model.query.filter_by(slug=slug).first()) and existing.id != obj_id:
        slug, n = f"{base}-{n}", n + 1
    return slug


def _project_before_save(form, obj):
    obj.slug = obj.slug or _unique_slug(Project, slugify(obj.title) or "project", obj.id)


def _category_before_save(form, obj):
    obj.slug = obj.slug or slugify(obj.label)
    clash = Category.query.filter_by(kind=obj.kind, slug=obj.slug).first()
    if clash and clash.id != obj.id:
        obj.slug = f"{obj.slug}-{Category.query.count() + 1}"


def _category_before_delete(obj):
    for model in (Project, Certificate):
        model.query.filter_by(category_id=obj.id).update({"category_id": None})


def _skills_load(form, obj):
    form.skills_text.data = [s.name for s in obj.skills]


def _skills_before_save(form, obj):
    existing = {s.name: s for s in obj.skills}
    obj.skills = [existing.get(name) or Skill(name=name) for name in form.skills_text.data]
    for i, skill in enumerate(obj.skills):
        skill.sort_order = i


def _prepare_categories(form):
    form.set_category_choices()


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
RESOURCES = {r.slug: r for r in [
    Resource(
        "projects", Project, forms.ProjectForm, "Projects", "Project", "fas fa-code",
        columns=[("Title", lambda o: o.title),
                 ("Category", lambda o: o.category.label if o.category else "—"),
                 ("Status", lambda o: Project.STATUSES.get(o.status, o.status)),
                 ("Tech", lambda o: ", ".join(o.tech or []))],
        uploads={"image_upload": ("image", "projects", IMAGES)},
        thumbnail="image", prepare_form=_prepare_categories, before_save=_project_before_save,
        public_url=lambda o: url_for("public.project_detail", slug=o.slug),
        description="Shown on the Projects page; each project also gets its own page.",
    ),
    Resource(
        "certificates", Certificate, forms.CertificateForm, "Certificates", "Certificate", "fas fa-certificate",
        columns=[("Title", lambda o: o.title), ("Issuer", lambda o: o.issuer),
                 ("Category", lambda o: o.category.label if o.category else "—")],
        uploads={"image_upload": ("image", "certificates", IMAGES),
                 "file_upload": ("file", "certificates", DOCUMENTS)},
        thumbnail="image", prepare_form=_prepare_categories,
        description="Shown on the Certificates page.",
    ),
    Resource(
        "experience", Experience, forms.ExperienceForm, "Experience", "Experience", "fas fa-briefcase",
        columns=[("Role", lambda o: o.title), ("Company", lambda o: o.company), ("Dates", _date_range)],
        uploads={"certificate_upload": ("certificate", "experience", DOCUMENTS)},
        description="Work experience timeline on the Resume page.",
    ),
    Resource(
        "education", Education, forms.EducationForm, "Education", "Education", "fas fa-graduation-cap",
        columns=[("Qualification", lambda o: o.title), ("Institution", lambda o: o.institution),
                 ("Dates", _date_range), ("Grade", lambda o: o.grade)],
        description="Education timeline on the Resume page.",
    ),
    Resource(
        "skills", SkillGroup, forms.SkillGroupForm, "Skills", "Skill group", "fas fa-layer-group",
        columns=[("Group", lambda o: o.name), ("Skills", lambda o: ", ".join(s.name for s in o.skills))],
        load_form=_skills_load, before_save=_skills_before_save,
        description="Skill groups on the Resume page.",
    ),
    Resource(
        "blogs", Blog, forms.BlogForm, "Blogs", "Blog post", "fas fa-pen-nib",
        columns=[("Title", lambda o: o.title), ("Link", lambda o: o.url)],
        uploads={"image_upload": ("image", "blogs", IMAGES)}, thumbnail="image",
        description="Article cards on the Blogs page.",
    ),
    Resource(
        "categories", Category, forms.CategoryForm, "Categories", "Category", "fas fa-tags",
        columns=[("Name", lambda o: o.label),
                 ("Used for", lambda o: "Projects" if o.kind == "project" else "Certificates"),
                 ("Slug", lambda o: o.slug), ("Icon", lambda o: o.icon)],
        before_save=_category_before_save, before_delete=_category_before_delete,
        description="Filter buttons for projects and certificates.",
    ),
    Resource(
        "social-links", SocialLink, forms.SocialLinkForm, "Social links", "Social link", "fas fa-share-nodes",
        columns=[("Name", lambda o: o.label), ("Icon", lambda o: o.icon), ("Link", lambda o: o.url)],
        description="Icons in the floating social bar.",
    ),
]}

NAV_GROUPS = [
    ("Content", ["projects", "certificates", "blogs"]),
    ("Resume", ["experience", "education", "skills"]),
    ("Site", ["categories", "social-links"]),
]
