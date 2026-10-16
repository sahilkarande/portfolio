"""Image optimisation: auto-rotate, strip metadata, resize, re-encode.

Every optimised image gets a sibling thumbnail named "<name>.thumb.<ext>", used for
cards and grids (see `thumb_path`).
"""
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 60_000_000  # reject decompression bombs (~7700×7700)


@dataclass(frozen=True)
class Preset:
    max_px: int        # longest side of the main image
    thumb_px: int      # longest side of the thumbnail
    fmt: str           # "webp" or "jpeg"
    quality: int = 82


# Keyed by upload folder ("kind").
PRESETS = {
    "projects": Preset(1600, 720, "webp"),
    "certificates": Preset(1400, 640, "webp"),
    "blogs": Preset(1400, 720, "webp"),
    # JPEG so social networks that don't read WebP still show it in link previews.
    "profile": Preset(1000, 480, "jpeg", 85),
}
DEFAULT_PRESET = Preset(1600, 720, "webp")
EXT = {"webp": "webp", "jpeg": "jpg"}


class ImageError(ValueError):
    pass


@dataclass
class Optimised:
    main: bytes
    thumb: bytes
    ext: str
    size: tuple[int, int]


def thumb_path(path):
    """'uploads/projects/a.webp' -> 'uploads/projects/a.thumb.webp'."""
    stem, dot, ext = path.rpartition(".")
    return f"{stem}.thumb.{ext}" if dot else f"{path}.thumb"


def _encode(img, preset, max_px):
    img = img.copy()
    img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    if preset.fmt == "jpeg" and img.mode != "RGB":
        background = Image.new("RGB", img.size, "white")  # flatten transparency onto white
        background.paste(img, mask=img.getchannel("A") if "A" in img.getbands() else None)
        img = background
    elif preset.fmt == "webp" and img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "transparency" in img.info or "A" in img.getbands() else "RGB")
    out = io.BytesIO()
    options = {"quality": preset.quality, "optimize": True}
    if preset.fmt == "webp":
        options["method"] = 6
    else:
        options["progressive"] = True
    img.save(out, preset.fmt.upper(), **options)  # no exif/icc passed -> metadata stripped
    return out.getvalue(), img.size


def optimise(source, kind):
    """Optimise an image from a file path or binary stream for the given upload kind."""
    preset = PRESETS.get(kind, DEFAULT_PRESET)
    try:
        with Image.open(source) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
        raise ImageError(f"Couldn't read that image ({e.__class__.__name__}).") from e
    main, size = _encode(img, preset, preset.max_px)
    thumb, _ = _encode(img, preset, preset.thumb_px)
    return Optimised(main=main, thumb=thumb, ext=EXT[preset.fmt], size=size)
