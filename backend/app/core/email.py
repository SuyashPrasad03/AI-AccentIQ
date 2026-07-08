"""
EmailSender abstraction.

Concrete implementations:
  SmtpEmailSender  — sends real email via SMTP (production / staging)
  ConsoleEmailSender — prints to stdout (development / CI when SMTP not configured)

The active sender is resolved at runtime based on settings.email_console_fallback.
Import `send_email` for fire-and-forget usage, or `get_email_sender()` for DI.
"""

import smtplib
import ssl
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class EmailSender(ABC):
    @abstractmethod
    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        """Send an email. Implementations must not raise on transient failures."""


class ConsoleEmailSender(EmailSender):
    """Prints email to stdout — use in development when SMTP is not configured."""

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        logger.info(
            "email_console_fallback",
            to=to,
            subject=subject,
            body=text_body,
        )
        print(
            f"\n{'='*60}\n"
            f"📧 EMAIL (console fallback)\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"Body:\n{text_body}\n"
            f"{'='*60}\n"
        )


class SmtpEmailSender(EmailSender):
    """Send email via SMTP with TLS."""

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            context = ssl.create_default_context()
            # Use SMTP_SSL for port 465, starttls for port 587
            if settings.smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(settings.smtp_from_address, to, msg.as_string())
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(settings.smtp_from_address, to, msg.as_string())

            logger.info("email_sent", to=to, subject=subject)
        except Exception as exc:
            # Log but don't raise — callers shouldn't fail because email is down
            logger.error("email_send_failed", to=to, subject=subject, error=str(exc))


def get_email_sender() -> EmailSender:
    """Return the appropriate EmailSender based on settings."""
    if settings.email_console_fallback or not settings.smtp_password:
        return ConsoleEmailSender()
    return SmtpEmailSender()


async def send_otp_email(to: str, otp: str, purpose: str = "registration") -> None:
    """Convenience function for sending an OTP email."""
    sender = get_email_sender()
    subject = "Your AccentIQ verification code"
    text_body = (
        f"Your {purpose} code is: {otp}\n\n"
        f"This code expires in {settings.otp_expiry_minutes} minutes.\n"
        "If you did not request this, please ignore this email."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
      <h2 style="color:#1e293b">AccentIQ</h2>
      <p>Your verification code:</p>
      <div style="font-size:2.5rem;font-weight:700;letter-spacing:0.25em;
                  color:#4f46e5;padding:16px;background:#f1f5f9;
                  border-radius:8px;text-align:center">{otp}</div>
      <p style="color:#64748b;font-size:0.9rem;margin-top:16px">
        This code expires in <strong>{settings.otp_expiry_minutes} minutes</strong>.
        If you did not request this, please ignore this email.
      </p>
    </div>
    """
    await sender.send(to=to, subject=subject, html_body=html_body, text_body=text_body)
