"""Письма. Без SMTP — демонстрационный режим: ссылка возвращается вызывающему коду и показывается на экране."""
import smtplib
from email.message import EmailMessage
from ..config import get_settings


def send_email(to: str, subject: str, text: str) -> bool:
    s = get_settings()
    if s.email_demo:
        return False
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as srv:
        srv.starttls()
        if s.smtp_user:
            srv.login(s.smtp_user, s.smtp_password)
        srv.send_message(msg)
    return True
