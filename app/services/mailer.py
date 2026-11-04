
import os
import asyncio
import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "http://localhost:3000"
).strip().rstrip("/")

# Configure Resend
resend.api_key = RESEND_API_KEY


async def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is missing from environment")

    def send_request():
        return resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": to.strip(),
            "subject": subject,
            "html": html,
        })

    try:
        result = await asyncio.to_thread(send_request)
        return {
            "success": True,
            "id": result.get("id") if isinstance(result, dict) else None
        }
    except Exception as error:
        raise RuntimeError(f"Resend email error: {str(error)}") from error


def verify_link(token: str) -> str:
    return f"{APP_BASE_URL}/auth/verify?token={token}"


def reset_link(token: str) -> str:
    return f"{APP_BASE_URL}/reset-password?token={token}"
