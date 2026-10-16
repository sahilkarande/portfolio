import json
from datetime import date
from pathlib import Path

import click
from flask import current_app
from slugify import slugify

from .config import BASE_DIR
from .extensions import db
from .models import (Blog, Category, Certificate, Education, Experience, Profile, Project, Skill,
                     SkillGroup, SocialLink, User)

SEED_FILE = BASE_DIR / "seed" / "initial_content.json"
CONTENT_MODELS = [Skill, SkillGroup, Project, Certificate, Category, Education, Experience, Blog,
                  SocialLink, Profile]


def _date(value):
    return date.fromisoformat(value) if value else None


def _link(value):
    return None if not value or value == "#" else value


def _seed(data):
    missing = []

    def static_path(rel):
        if rel and not (Path(current_app.static_folder) / rel).exists():
            missing.append(rel)
        return rel

    db.session.add(Profile(id=1, **data["profile"]))
    for i, s in enumerate(data["social_links"]):
        db.session.add(SocialLink(sort_order=i, **s))

    categories = {}
    for kind, key in (("project", "project_categories"), ("certificate", "certificate_categories")):
        for i, c in enumerate(cat for cat in data[key] if cat["id"] != "all"):
            categories[kind, c["id"]] = Category(kind=kind, slug=c["id"], label=c["label"],
                                                 icon=c["icon"], sort_order=i)
            db.session.add(categories[kind, c["id"]])

    used_slugs = set()
    for i, p in enumerate(data["projects"]):
        slug = base = slugify(p["title"])
        n = 2
        while slug in used_slugs:
            slug, n = f"{base}-{n}", n + 1
        used_slugs.add(slug)
        link = _link(p["link"])
        is_repo = bool(link and "github.com" in link)
        db.session.add(Project(
            title=p["title"], slug=slug, summary=p["description"], tech=p["tech"],
            image=static_path(f"assets/images/{p['image']}"), status=p["status"],
            repo_url=link if is_repo else None, live_url=None if is_repo else link,
            category=categories.get(("project", p["category"])), sort_order=i,
        ))

    for i, c in enumerate(data["certificates"]):
        db.session.add(Certificate(
            title=c["title"], issuer=c["issuer"], credential_url=_link(c["link"]),
            image=static_path(f"assets/certificates/Images/{c['image']}"),
            category=categories.get(("certificate", c["category"])), sort_order=i,
        ))

    for i, e in enumerate(data["education"]):
        db.session.add(Education(
            title=e["title"], institution=e["institution"], location=e["location"],
            start_date=_date(e["startDate"]), end_date=_date(e["endDate"]),
            current=e.get("current", False), grade=e.get("grade", ""),
            courses=e.get("courses") or [], sort_order=i,
        ))

    for i, e in enumerate(data["experience"]):
        db.session.add(Experience(
            title=e["title"], company=e["company"], company_url=e.get("companyLink"),
            location=e["location"], start_date=_date(e["startDate"]), end_date=_date(e["endDate"]),
            current=e.get("current", False), highlights=e.get("description") or [],
            certificate=static_path(e["certificate"]) if e.get("certificate") else None, sort_order=i,
        ))

    for i, (group, names) in enumerate(data["skills"].items()):
        db.session.add(SkillGroup(name=group, sort_order=i,
                                  skills=[Skill(name=n, sort_order=j) for j, n in enumerate(names)]))

    for i, b in enumerate(data["blogs"]):
        db.session.add(Blog(title=b["title"], summary=b["description"], image=b["image"],
                            url=b["link"], sort_order=i))

    db.session.commit()
    return missing


def register(app):
    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="Delete existing content first.")
    def seed(force):
        """Load the original portfolio content from seed/initial_content.json."""
        if db.session.get(Profile, 1) is not None:
            if not force:
                raise click.ClickException("Content already exists. Re-run with --force to replace it.")
            click.confirm("This deletes all projects, certificates, resume and blog content. Continue?",
                          abort=True)
            for model in CONTENT_MODELS:
                db.session.query(model).delete()
            db.session.commit()

        missing = _seed(json.loads(SEED_FILE.read_text(encoding="utf-8")))
        click.secho("Seeded portfolio content.", fg="green")
        if missing:
            click.secho(f"{len(missing)} referenced files are missing from static/ "
                        "(fix them later from the admin panel):", fg="yellow")
            for path in missing:
                click.echo(f"  - {path}")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option(help="At least 10 characters.")
    def create_admin(username, password):
        """Create the admin user, or reset the password of an existing one."""
        if len(password) < 10:
            raise click.ClickException("Password must be at least 10 characters.")
        user = User.query.filter_by(username=username).first()
        created = user is None
        user = user or User(username=username)
        user.set_password(password)
        user.failed_logins, user.locked_until = 0, None
        db.session.add(user)
        db.session.commit()
        click.secho(f"Admin '{username}' {'created' if created else 'password reset'}.", fg="green")

    @app.cli.command("optimize-images")
    @click.option("--dry-run", is_flag=True, help="Only report what would change.")
    def optimize_images(dry_run):
        """Create optimised copies of images that were added before auto-optimisation."""
        from .services.media import OPTIMISED, UPLOAD_PREFIX, UploadError, store_optimised

        targets = [(Project, "image", "projects"), (Certificate, "image", "certificates"),
                   (Blog, "image", "blogs"), (Profile, "avatar", "profile")]
        static = Path(current_app.static_folder)
        before = after = done = 0
        for model, attr, kind in targets:
            for obj in model.query.all():
                path = getattr(obj, attr)
                if (not path or path.startswith((UPLOAD_PREFIX, "http://", "https://"))
                        or path.rsplit(".", 1)[-1].lower() not in OPTIMISED):
                    continue
                source = static / path
                if not source.is_file():
                    click.secho(f"  missing: {path}", fg="yellow")
                    continue
                if dry_run:
                    click.echo(f"  would optimise {path} ({source.stat().st_size // 1024} KB)")
                    continue
                try:
                    new_path = store_optimised(source, kind, source.name)
                except UploadError as e:
                    click.secho(f"  skipped {path}: {e}", fg="yellow")
                    continue
                new_size = (Path(current_app.config["UPLOAD_FOLDER"]) / new_path[len(UPLOAD_PREFIX):]).stat().st_size
                before += source.stat().st_size
                after += new_size
                done += 1
                setattr(obj, attr, new_path)
                click.echo(f"  {path}: {source.stat().st_size // 1024} KB -> {new_size // 1024} KB")
        if not dry_run:
            db.session.commit()
            saved = (1 - after / before) * 100 if before else 0
            click.secho(f"Optimised {done} images: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB "
                        f"({saved:.0f}% smaller). Originals in static/assets were left untouched.", fg="green")

    @app.cli.command("backup")
    @click.option("--dest", default=str(BASE_DIR.parent / "backups"), show_default=True,
                  help="Folder to write backups to (keep it outside the git checkout).")
    @click.option("--keep", default=14, show_default=True, help="How many backups to keep.")
    def backup(dest, keep):
        """Back up the database and uploaded files to a timestamped .tar.gz."""
        import os
        import shutil
        import subprocess
        import tarfile
        import tempfile

        from .models import utcnow

        url = db.engine.url
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        stamp = utcnow().strftime("%Y%m%d-%H%M%S")
        archive = dest / f"portfolio-{stamp}.tar.gz"

        with tempfile.TemporaryDirectory() as tmp:
            if url.get_backend_name() == "sqlite":
                dump = Path(tmp) / "database.sqlite"
                shutil.copy2(url.database, dump)
            elif url.get_backend_name() == "mysql":
                dump = Path(tmp) / "database.sql"
                cmd = ["mysqldump", "--single-transaction", "--no-tablespaces", "--set-gtid-purged=OFF",
                       "-h", url.host, "-u", url.username]
                if url.port:
                    cmd += ["-P", str(url.port)]
                cmd.append(url.database)
                env = {**os.environ, "MYSQL_PWD": url.password or ""}  # keeps the password out of `ps`
                with open(dump, "wb") as out:
                    result = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, env=env)
                if result.returncode != 0:
                    raise click.ClickException(f"mysqldump failed: {result.stderr.decode().strip()}")
            else:
                raise click.ClickException(f"Backups aren't supported for {url.get_backend_name()}.")

            with tarfile.open(archive, "w:gz") as tar:
                tar.add(dump, arcname=dump.name)
                uploads = Path(current_app.config["UPLOAD_FOLDER"])
                if uploads.is_dir():
                    tar.add(uploads, arcname="uploads")

        old = sorted(dest.glob("portfolio-*.tar.gz"))[:-keep] if keep > 0 else []
        for path in old:
            path.unlink()
        click.secho(f"Backup written: {archive} ({archive.stat().st_size / 1e6:.1f} MB); "
                    f"removed {len(old)} old backup(s).", fg="green")
