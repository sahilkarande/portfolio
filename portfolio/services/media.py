"""Saving, validating and deleting uploaded files.

Uploads are stored at  UPLOAD_FOLDER/<kind>/<random>-<name>  and referenced in the
database as  "uploads/<kind>/<random>-<name>"  (relative to the static folder).
Only paths under "uploads/" are ever deleted, so original files in static/assets
are never touched.
"""
import secrets
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from .images import ImageError, optimise, thumb_path

UPLOAD_PREFIX = "uploads/"

# SVG is intentionally excluded: it can carry scripts and is served from our own origin.
IMAGE_SIGNATURES = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],
}
DOCUMENT_SIGNATURES = {"pdf": [b"%PDF-"]}

IMAGES = set(IMAGE_SIGNATURES)
DOCUMENTS = set(DOCUMENT_SIGNATURES)
SIGNATURES = IMAGE_SIGNATURES | DOCUMENT_SIGNATURES


# GIFs are stored as-is (re-encoding would drop animation).
OPTIMISED = IMAGES - {"gif"}


class UploadError(ValueError):
    pass


def _unique_name(original_name, ext):
    stem = secure_filename(original_name.rsplit(".", 1)[0])[:60] or "file"
    return f"{secrets.token_hex(4)}-{stem}.{ext}"


def store_optimised(source, kind, original_name):
    """Optimise an image (path or stream), write it + its thumbnail, return the stored path."""
    try:
        result = optimise(source, kind)
    except ImageError as e:
        raise UploadError(str(e)) from e
    name = _unique_name(original_name, result.ext)
    folder = Path(current_app.config["UPLOAD_FOLDER"]) / kind
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(result.main)
    (folder / thumb_path(name)).write_bytes(result.thumb)
    return f"{UPLOAD_PREFIX}{kind}/{name}"


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def save_upload(file_storage, kind, allowed):
    """Validate and store an uploaded file. Returns the stored path, or None if no file."""
    if not file_storage or not file_storage.filename:
        return None

    ext = _extension(file_storage.filename)
    if ext not in allowed:
        raise UploadError(f"'.{ext}' files aren't allowed here (use: {', '.join(sorted(allowed))}).")

    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in SIGNATURES[ext]):
        raise UploadError(f"{file_storage.filename} doesn't look like a real .{ext} file.")
    if ext == "webp" and head[8:12] != b"WEBP":
        raise UploadError(f"{file_storage.filename} doesn't look like a real .webp file.")

    if ext in OPTIMISED:
        return store_optimised(file_storage.stream, kind, file_storage.filename)

    name = _unique_name(file_storage.filename, ext)
    folder = Path(current_app.config["UPLOAD_FOLDER"]) / kind
    folder.mkdir(parents=True, exist_ok=True)
    file_storage.save(folder / name)
    return f"{UPLOAD_PREFIX}{kind}/{name}"


def delete_upload(path):
    """Delete a previously uploaded file. Ignores URLs and non-upload paths."""
    if not path or not path.startswith(UPLOAD_PREFIX):
        return
    root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target = (root / path[len(UPLOAD_PREFIX):]).resolve()
    for candidate in (target, target.with_name(thumb_path(target.name))):
        if root in candidate.parents and candidate.is_file():
            candidate.unlink()


def file_exists(path):
    """True for URLs, and for static paths that exist on disk."""
    if not path or path.startswith(("http://", "https://")):
        return True
    if path.startswith(UPLOAD_PREFIX):
        return (Path(current_app.config["UPLOAD_FOLDER"]) / path[len(UPLOAD_PREFIX):]).is_file()
    return (Path(current_app.static_folder) / path.lstrip("/").removeprefix("static/")).is_file()


def thumb_url_path(path):
    """Thumbnail for an uploaded image if one exists, else the original path/URL."""
    if path and path.startswith(UPLOAD_PREFIX):
        thumb = thumb_path(path)
        if (Path(current_app.config["UPLOAD_FOLDER"]) / thumb[len(UPLOAD_PREFIX):]).is_file():
            return thumb
    return path
