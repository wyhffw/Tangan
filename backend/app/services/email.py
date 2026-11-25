

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    def __init__(self, *, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_username and settings.smtp_password)


def send_mail(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    settings = get_settings()
    if not smtp_configured():
        raise EmailError(
            status_code=503, detail="邮件发送尚未配置", code="smtp_unconfigured"
        )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_username}>"
    message["To"] = to
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except smtplib.SMTPException as exc:
        logger.warning("send_mail failed: %s", exc)
        raise EmailError(
            status_code=502, detail="邮件发送失败，请检查发信配置", code="smtp_error"
        ) from exc
