"""Sending email: through the configured mail server, or into instance/outbox/ when there isn't one.

Emails are rendered in the request (so links can be absolute) and sent on a background
thread, so a slow or failing mail server never holds up checkout or the admin.
"""

import logging
import os
import re
from threading import Thread

from flask import current_app
from flask_mail import Message

from app.extension import mail

log = logging.getLogger(__name__)


def outbox_dir(app):
    return os.path.join(app.instance_path, "outbox")


def uses_outbox(app):
    """No mail server configured (and not testing): keep emails as files instead of sending."""
    return not app.config.get("MAIL_SERVER") and not app.testing


def _write_outbox(app, msg):
    folder = outbox_dir(app)
    os.makedirs(folder, exist_ok=True)
    from app.models import utcnow

    stamp = utcnow().strftime("%Y%m%d-%H%M%S-%f")
    slug = re.sub(r"[^a-z0-9]+", "-", msg.subject.lower()).strip("-")[:60]
    base = os.path.join(folder, f"{stamp}-{slug}")
    with open(base + ".html", "w") as fh:
        fh.write(f"<!-- To: {', '.join(msg.recipients)} | Subject: {msg.subject} -->\n{msg.html or ''}")
    with open(base + ".eml", "wb") as fh:
        fh.write(msg.as_bytes())
    log.info("Email to %s saved to %s.html (no MAIL_SERVER set)", msg.recipients, base)
    return base


def _send(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception:  # a mail problem must never break the page that triggered it
            log.exception("Sending email %r to %s failed", msg.subject, msg.recipients)


def send(subject, recipients, html, text, reply_to=None):
    """Send an email (in the background), or save it to the outbox. Returns the Message."""
    recipients = [r for r in recipients if r]
    if not recipients:
        return None
    app = current_app._get_current_object()
    msg = Message(subject, sender=app.config["MAIL_SENDER"], recipients=recipients, reply_to=reply_to)
    msg.html = html
    msg.body = text
    if uses_outbox(app):
        _write_outbox(app, msg)
    elif app.testing:
        mail.send(msg)  # suppressed in tests; recorded by mail.record_messages()
    else:
        Thread(target=_send, args=(app, msg), daemon=True).start()
    return msg
