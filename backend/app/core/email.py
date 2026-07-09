"""
EmailSender abstraction.

Concrete implementations:
  HttpEmailSender    — sends via HTTP API (Render/serverless where SMTP ports are blocked)
  SmtpEmailSender    — sends real email via SMTP (when outbound SMTP is available)
  ConsoleEmailSender — prints to stdout (development / CI when SMTP not configured)

The active sender is resolved at runtime based on settings.
Import `send_email` for fire-and-forget usage, or `get_email_sender()` for DI.
"""

import json
import smtplib
import ssl
import urllib.request
import urllib.error
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


class HttpEmailSender(EmailSender):
    """Send email via Brevo (Sendinblue) HTTP API — works on platforms that block SMTP.
    Free tier: 300 emails/day, no domain verification needed."""

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        api_key = settings.brevo_api_key
        if not api_key:
            # Fallback: try Resend
            if settings.resend_api_key:
                await self._send_resend(to=to, subject=subject, html_body=html_body, text_body=text_body)
                return
            logger.error("email_http_no_api_key", to=to)
            return

        payload = json.dumps({
            "sender": {"name": settings.smtp_from_name, "email": settings.smtp_from_address},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": text_body,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.info("email_sent_http", to=to, subject=subject, status=resp.status, provider="brevo")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error("email_http_failed", to=to, status=exc.code, body=body, provider="brevo")
        except Exception as exc:
            logger.error("email_http_error", to=to, error=str(exc), provider="brevo")

    async def _send_resend(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        """Fallback to Resend API."""
        payload = json.dumps({
            "from": f"{settings.smtp_from_name} <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.info("email_sent_http", to=to, subject=subject, status=resp.status, provider="resend")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error("email_http_failed", to=to, status=exc.code, body=body, provider="resend")
        except Exception as exc:
            logger.error("email_http_error", to=to, error=str(exc), provider="resend")


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
    """Return the appropriate EmailSender based on settings.
    
    Priority:
      1. Brevo HTTP API (if BREVO_API_KEY is set) — works everywhere, any recipient
      2. Resend HTTP API (if RESEND_API_KEY is set) — limited to account email on free tier
      3. SMTP (if smtp_password is set and not in dev-console mode)
      4. Console fallback
    """
    # Prefer HTTP API — works on platforms that block SMTP (Render, Railway, etc.)
    if settings.brevo_api_key or settings.resend_api_key:
        return HttpEmailSender()

    # Fall back to SMTP if credentials are available
    if settings.smtp_password and settings.smtp_host:
        if settings.email_console_fallback and settings.app_env == "development":
            return ConsoleEmailSender()
        return SmtpEmailSender()

    return ConsoleEmailSender()


async def send_otp_email(to: str, otp: str, purpose: str = "registration") -> None:
    """Convenience function for sending an OTP email."""
    sender = get_email_sender()
    logger.info(
        "otp_email_sending",
        to=to,
        sender_type=type(sender).__name__,
        smtp_host=settings.smtp_host,
        app_env=settings.app_env,
    )
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
