"""schema.org structured data (JSON-LD) so search engines understand who and what this is."""
from flask import current_app, request

from ..models import media_url


def site_root():
    """Public base URL without trailing slash: SITE_URL if configured, else this request's host."""
    return (current_app.config.get("SITE_URL") or request.url_root).rstrip("/")


def _abs(site_root, path):
    url = media_url(path)
    if not url:
        return None
    return url if url.startswith("http") else site_root + url


def person(profile, social_links, education, skills, site_root):
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": profile.name,
        "url": site_root + "/",
        "jobTitle": profile.role or None,
        "description": profile.headline or profile.meta_description or None,
        "image": _abs(site_root, profile.avatar),
        "email": f"mailto:{profile.email}" if profile.email else None,
        "worksFor": {"@type": "Organization", "name": profile.organization} if profile.organization else None,
        "address": {"@type": "PostalAddress", "addressLocality": profile.location} if profile.location else None,
        "alumniOf": [{"@type": "EducationalOrganization", "name": e.institution} for e in education] or None,
        "knowsAbout": skills[:30] or None,
        "sameAs": [s.url for s in social_links if s.url.startswith("http")] or None,
    }
    return {k: v for k, v in data.items() if v}


def website(profile, site_root):
    return {"@context": "https://schema.org", "@type": "WebSite", "name": f"{profile.name} — Portfolio",
            "url": site_root + "/"}


def project(proj, profile, page_url, site_root, projects_url):
    work = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode" if proj.repo_url else "CreativeWork",
        "name": proj.title,
        "description": proj.summary,
        "url": page_url,
        "image": _abs(site_root, proj.image),
        "author": {"@type": "Person", "name": profile.name, "url": site_root + "/"},
        "dateModified": proj.updated_at.date().isoformat() if proj.updated_at else None,
        "keywords": ", ".join(proj.tech or []) or None,
        "codeRepository": proj.repo_url,
        "programmingLanguage": proj.tech[:5] if proj.repo_url and proj.tech else None,
        "genre": proj.category.label if proj.category else None,
    }
    breadcrumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site_root + "/"},
            {"@type": "ListItem", "position": 2, "name": "Projects", "item": projects_url},
            {"@type": "ListItem", "position": 3, "name": proj.title, "item": page_url},
        ],
    }
    return [{k: v for k, v in work.items() if v}, breadcrumbs]
