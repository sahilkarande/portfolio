import logging
import smtplib
from email.message import EmailMessage

from flask import current_app, render_template

log = logging.getLogger(__name__)


def _build(subject, to, template, **context):
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_USERNAME"]
    msg["To"] = to
    html = render_template(template, **context)  # Jinja autoescapes visitor input
    msg.set_content("Please view this message in an HTML-capable mail client.")
    msg.add_alternative(html, subtype="html")
    return msg


def send_contact_emails(message, profile):
    """Notify the owner and send the visitor a confirmation. Returns True on success."""
    cfg = current_app.config
    if not (cfg["MAIL_USERNAME"] and cfg["MAIL_PASSWORD"]):
        log.warning("Mail credentials not configured; skipping email for message %s", message.id)
        return False

    owner = cfg["OWNER_EMAIL"] or cfg["MAIL_USERNAME"]
    emails = [
        _build(f"New contact message from {message.name}", owner,
               "email/owner_notification.html", message=message),
        _build("Thanks for reaching out!", message.email,
               "email/visitor_confirmation.html", message=message, profile=profile,
               site_url=cfg["SITE_URL"]),
    ]
    try:
        with smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=15) as smtp:
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            for email in emails:
                smtp.send_message(email)
        return True
    except (smtplib.SMTPException, OSError):
        log.exception("Failed to send contact emails for message %s", message.id)
        return False
