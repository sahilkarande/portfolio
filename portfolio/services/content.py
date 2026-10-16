"""Markdown → safe HTML for long-form content (project write-ups)."""
import markdown
import nh3
from markupsafe import Markup

ALLOWED_TAGS = {
    "h2", "h3", "h4", "p", "br", "hr", "strong", "em", "del", "a", "ul", "ol", "li",
    "blockquote", "code", "pre", "img", "table", "thead", "tbody", "tr", "th", "td",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}, "img": {"src", "alt", "title"}, "th": {"align"}, "td": {"align"}}


def render_markdown(text):
    if not text:
        return Markup("")
    html = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
    # Markdown allows raw HTML, so sanitise the result; nh3 also adds rel="noopener noreferrer".
    return Markup(nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                            url_schemes={"http", "https", "mailto"}))
