import os
from email.message import EmailMessage
import aiosmtplib

GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Relvo").strip()
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000").strip()

async def send_email(to: str, subject: str, html: str):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD not set")

    msg = EmailMessage()
    msg["From"] = f"{EMAIL_FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-capable email client.")  # plain fallback
    msg.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_APP_PASSWORD,
        timeout=20,
    )

    return {"success": True}

def verify_link(token: str) -> str:
    return f"{APP_BASE_URL}/auth/verify?token={token}"

def reset_link(token: str) -> str:
    return f"{APP_BASE_URL}/reset-password?token={token}"
