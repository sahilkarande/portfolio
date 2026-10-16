# Portfolio

**Deploying / updating the live site:** see [deploy/DEPLOY.md](deploy/DEPLOY.md).

Flask + SQLAlchemy portfolio. All content (profile, projects, certificates, resume, skills,
blogs, social links) lives in the database, not in the templates.

## Layout

```
app.py                    entry point (WSGI: `from app import app as application`)
portfolio/
  __init__.py             create_app() factory, template globals, error pages
  config.py               settings; DB picked from DATABASE_URL / MYSQL_* / SQLite fallback
  extensions.py           db, migrate, csrf
  models.py               all tables
  commands.py             `flask seed`
  public/                 public pages + contact form
  admin/                  /admin panel: auth, generic CRUD (resources.py), profile, inbox
  services/mailer.py      contact-form emails
  services/media.py       upload validation, storage and cleanup
migrations/               Alembic migrations (run `flask db upgrade` after pulling)
seed/initial_content.json original site content, loaded by `flask seed`
templates/, static/       pages and assets; uploads go to static/uploads/
tests/                    pytest suite
```

## Local development

```bash
python3 -m venv env && source env/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # set FLASK_ENV_NAME=development and a SECRET_KEY
flask --app app db upgrade      # create tables (SQLite at instance/portfolio.db)
flask --app app seed            # load original content
flask --app app optimize-images # one-off: compress the seeded images (originals untouched)
flask --app app create-admin    # your admin login (re-run to reset a password)
flask --app app run --debug     # site: http://127.0.0.1:5000  admin: /admin
python -m pytest -q
```

## Changing the database schema

1. Edit `portfolio/models.py`
2. `flask --app app db migrate -m "describe change"` and review the generated file
3. `flask --app app db upgrade` (locally, then on the server)

## Admin panel (`/admin`)

- Manage projects, certificates, blogs, experience, education, skills, categories, social links
  and your profile (photo, about text, resume PDF, contact details, SEO).
- Drag rows to reorder; click **Visible/Hidden** to publish or hide without deleting.
- Uploads (png/jpg/gif/webp/pdf, max 16 MB) are content-checked and saved to `static/uploads/`.
  Replacing or deleting an item removes its old uploaded file; original files in
  `static/assets/` are never deleted.
- Contact messages are stored in the inbox even if the email notification fails.
- Locked for 15 minutes after 5 wrong passwords. Forgot it? `flask --app app create-admin`
  with the same username resets it.

### Adding a new content type
Add a model in `models.py`, a form in `admin/forms.py`, one `Resource(...)` entry in
`admin/resources.py`, then `flask db migrate` + `flask db upgrade`.

## Images
Uploaded images are auto-rotated, stripped of metadata (GPS, camera), resized and saved as
WebP (profile photo as JPEG for social previews), plus a `.thumb` copy used on cards.
`flask optimize-images` does the same for images that were added before this existed.

## Project pages & SEO
- Every project has its own page at `/projects/<slug>`; the admin "Full write-up" field supports
  Markdown (sanitised). Hidden projects are visible only to you, as a preview.
- `/sitemap.xml`, `/robots.txt`, canonical URLs, Open Graph/Twitter tags and schema.org JSON-LD
  (Person on the home page, SoftwareSourceCode + breadcrumbs on project pages).
  Set `SITE_URL` in `.env` so these use your real domain.
- Google Search Console files in `static/assets/google*.html` are served at the site root.

## Analytics (`/admin/analytics`)
First-party and cookie-free: page views, daily visitors, top projects, referrers, devices and
outbound clicks (resume downloads, GitHub, live demos, socials). No IP addresses are stored — a
visitor is a daily-rotating hash — and bots, Do-Not-Track/GPC browsers and your own logged-in
visits are skipped. Events older than `ANALYTICS_RETENTION_DAYS` (default 395) are pruned.
