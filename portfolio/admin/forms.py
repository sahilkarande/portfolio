from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (BooleanField, DateField, PasswordField, SelectField, StringField, TextAreaField,
                     ValidationError)
from wtforms.validators import URL, DataRequired, EqualTo, Length, Optional

from ..models import Category, Project
from ..services.media import DOCUMENTS, IMAGES


# --------------------------------------------------------------------------- #
# Custom fields
# --------------------------------------------------------------------------- #
class LinesField(TextAreaField):
    """A list of strings edited as one item per line."""

    def _value(self):
        return "\n".join(self.data or [])

    def process_formdata(self, valuelist):
        self.data = [line.strip() for line in (valuelist[0] if valuelist else "").splitlines() if line.strip()]


class TagsField(StringField):
    """A list of strings edited as comma-separated text."""

    def _value(self):
        return ", ".join(self.data or [])

    def process_formdata(self, valuelist):
        self.data = [t.strip() for t in (valuelist[0] if valuelist else "").split(",") if t.strip()]


def _int_or_none(value):
    return int(value) if value not in (None, "", "None") else None


def link_url(form, field):
    """Like URL() but also accepts mailto:/tel: and site-relative paths."""
    if field.data and not field.data.startswith(("http://", "https://", "mailto:", "tel:", "/")):
        raise ValidationError("Must start with https://, mailto:, tel: or /")


def image_upload(label="Upload image"):
    return FileField(label, description=f"Allowed: {', '.join(sorted(IMAGES))}")


def pdf_upload(label="Upload PDF"):
    return FileField(label, description="Allowed: pdf")


def path_field(label, description="Filled in automatically when you upload. You can also paste a URL."):
    return StringField(label, validators=[Optional(), Length(max=500)], description=description)


url_field = lambda label: StringField(label, validators=[Optional(), URL(), Length(max=500)])  # noqa: E731


class CategorySelectMixin:
    category_kind = None

    def set_category_choices(self):
        cats = Category.query.filter_by(kind=self.category_kind).order_by(Category.sort_order).all()
        self.category_id.choices = [("", "— No category —")] + [(c.id, c.label) for c in cats]


# --------------------------------------------------------------------------- #
# Content forms
# --------------------------------------------------------------------------- #
class ProjectForm(CategorySelectMixin, FlaskForm):
    category_kind = "project"

    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    slug = StringField("URL slug", validators=[Optional(), Length(max=220)],
                       description="Leave blank to generate from the title.")
    summary = TextAreaField("Short description", validators=[DataRequired(), Length(max=500)],
                            description="Shown on the project card (max 500 characters).")
    category_id = SelectField("Category", coerce=_int_or_none, validate_choice=False)
    status = SelectField("Status", choices=list(Project.STATUSES.items()))
    tech = TagsField("Tech stack", description="Comma separated, e.g. Python, Flask, MySQL")
    repo_url = url_field("GitHub / source URL")
    live_url = url_field("Live demo URL")
    image_upload = image_upload("Cover image")
    image = path_field("Image path / URL")
    body = TextAreaField("Full write-up (optional)", validators=[Optional()],
                         description="Shown on the project's own page. Markdown: ## Heading, **bold**, *italic*, "
                                     "- bullet, 1. list, [link](https://…), ![image](https://…), `code`, ``` code block ```.")
    featured = BooleanField("Featured project")
    is_published = BooleanField("Published (visible on site)", default=True)

    def validate_slug(self, field):
        if field.data:
            existing = Project.query.filter_by(slug=field.data).first()
            if existing and existing.id != getattr(self, "_obj_id", None):
                raise ValidationError("Another project already uses this slug.")


class CertificateForm(CategorySelectMixin, FlaskForm):
    category_kind = "certificate"

    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    issuer = StringField("Issued by", validators=[Optional(), Length(max=160)])
    category_id = SelectField("Category", coerce=_int_or_none, validate_choice=False)
    issued_on = DateField("Issue date", validators=[Optional()])
    credential_url = url_field("Credential / verification URL")
    image_upload = image_upload("Certificate image (thumbnail)")
    image = path_field("Image path / URL")
    file_upload = pdf_upload("Certificate PDF")
    file = path_field("PDF path / URL", "Visitors open this if no credential URL is set.")
    is_published = BooleanField("Published (visible on site)", default=True)


class EducationForm(FlaskForm):
    title = StringField("Degree / qualification", validators=[DataRequired(), Length(max=200)])
    institution = StringField("Institution", validators=[DataRequired(), Length(max=200)])
    location = StringField("Location", validators=[Optional(), Length(max=160)])
    start_date = DateField("Start date", validators=[Optional()])
    end_date = DateField("End date", validators=[Optional()])
    current = BooleanField("Currently studying here")
    grade = StringField("Grade", validators=[Optional(), Length(max=60)], description="e.g. CGPA: 8.13")
    courses = LinesField("Courses / subjects", description="One per line.")


class ExperienceForm(FlaskForm):
    title = StringField("Job title", validators=[DataRequired(), Length(max=200)])
    company = StringField("Company / organisation", validators=[DataRequired(), Length(max=200)])
    company_url = url_field("Company website")
    location = StringField("Location", validators=[Optional(), Length(max=160)])
    start_date = DateField("Start date", validators=[Optional()])
    end_date = DateField("End date", validators=[Optional()])
    current = BooleanField("I currently work here")
    highlights = LinesField("Responsibilities / achievements", description="One bullet point per line.")
    certificate_upload = pdf_upload("Experience certificate / letter")
    certificate = path_field("Certificate path / URL")


class SkillGroupForm(FlaskForm):
    name = StringField("Group name", validators=[DataRequired(), Length(max=120)],
                       description="e.g. Big Data Technologies")
    icon = StringField("Icon (optional)", validators=[Optional(), Length(max=60)],
                       description="Font Awesome class, e.g. fas fa-database")
    skills_text = LinesField("Skills", description="One skill per line, in display order.")


class BlogForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    summary = TextAreaField("Summary", validators=[Optional(), Length(max=500)])
    url = StringField("Article URL", validators=[DataRequired(), URL(), Length(max=500)],
                      description="Link to the post on Medium, Hashnode, etc.")
    published_on = DateField("Published on", validators=[Optional()])
    image_upload = image_upload("Cover image")
    image = path_field("Image path / URL")
    is_published = BooleanField("Published (visible on site)", default=True)


class CategoryForm(FlaskForm):
    kind = SelectField("Used for", choices=[("project", "Projects"), ("certificate", "Certificates")])
    label = StringField("Name", validators=[DataRequired(), Length(max=120)])
    slug = StringField("Slug", validators=[Optional(), Length(max=80)],
                       description="Leave blank to generate from the name.")
    icon = StringField("Icon", validators=[Optional(), Length(max=60)], default="fas fa-folder",
                       description="Font Awesome class, e.g. fas fa-brain")


class SocialLinkForm(FlaskForm):
    label = StringField("Name", validators=[DataRequired(), Length(max=60)], description="e.g. GitHub")
    icon = StringField("Icon", validators=[DataRequired(), Length(max=60)],
                       description="Font Awesome class, e.g. fab fa-github")
    url = StringField("Link", validators=[DataRequired(), link_url, Length(max=500)],
                      description="https://…, mailto:you@example.com or tel:+91…")


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    role = StringField("Current role", validators=[Optional(), Length(max=120)])
    organization = StringField("Organisation", validators=[Optional(), Length(max=160)])
    headline = StringField("Headline", validators=[Optional(), Length(max=255)],
                           description="Shown under “About Me”.")
    about_html = TextAreaField("About text", validators=[Optional()],
                               description="HTML allowed: wrap paragraphs in <p>…</p>, bold with <b>…</b>.")
    years_experience = StringField("Years of experience", validators=[Optional(), Length(max=20)])
    education_summary = StringField("Education (sidebar)", validators=[Optional(), Length(max=255)],
                                    description="Use <br> for a line break.")
    expertise_summary = StringField("Expertise (sidebar)", validators=[Optional(), Length(max=255)])
    location = StringField("Location", validators=[Optional(), Length(max=160)])
    email = StringField("Public email", validators=[Optional(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    avatar_upload = image_upload("Profile photo")
    avatar = path_field("Photo path / URL")
    resume_upload = pdf_upload("Resume PDF")
    resume_file = path_field("Resume path / URL")
    map_label = StringField("Map caption", validators=[Optional(), Length(max=160)])
    map_embed_url = StringField("Google Maps embed URL", validators=[Optional(), URL()],
                                description="Google Maps → Share → Embed a map → copy the src=\"…\" URL.")
    meta_description = TextAreaField("SEO description", validators=[Optional(), Length(max=300)])
    meta_keywords = StringField("SEO keywords", validators=[Optional(), Length(max=300)])


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)],
                                 description="At least 10 characters.")
    confirm = PasswordField("Confirm new password",
                            validators=[DataRequired(), EqualTo("new_password", "Passwords don't match.")])
