"""Outbound email using only the standard library (no extra dependency).

EMAIL_BACKEND=console writes messages to the log instead of sending them. It is
meant for local development and is refused in production by Settings.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    if settings.EMAIL_BACKEND == "console":
        logger.warning("Email not sent (EMAIL_BACKEND=console, development only):\n%s", message)
        return

    context = ssl.create_default_context()
    if settings.SMTP_SECURITY == "tls":
        smtp = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS, context=context)
    else:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
    with smtp:
        if settings.SMTP_SECURITY == "starttls":
            smtp.starttls(context=context)
        if settings.SMTP_USERNAME:
            password = settings.SMTP_PASSWORD.get_secret_value() if settings.SMTP_PASSWORD else ""
            smtp.login(settings.SMTP_USERNAME, password)
        smtp.send_message(message)
