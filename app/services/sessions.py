import hashlib
import os
import secrets
from fastapi import Response

from .tokens import utcnow

COOKIE_NAME = "nf_session"
ORG_COOKIE_NAME = "nf_org"
ONBOARDING_COOKIE_NAME = "nf_onboarding"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(resp: Response, token: str, minutes: int = 60 * 24 * 7):
    is_prod = os.getenv("ENV") == "production"
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        domain=".neuroflowai.co.uk" if is_prod else None,
        max_age=minutes * 60,
        path="/",
    )


def clear_session_cookie(resp: Response):
    is_prod = os.getenv("ENV") == "production"
    resp.delete_cookie(
        COOKIE_NAME,
        path="/",
        domain=".neuroflowai.co.uk" if is_prod else None,
    )


# ── org cookie ────────────────────────────────────────────────────────────────

def set_org_cookie(resp: Response, org_id: str, minutes: int = 60 * 24 * 7):
    """
    Set the nf_org cookie so the Next.js proxy can read it without
    making an API call. NOT httponly — proxy needs to read it.
    Value is just the org UUID (not sensitive).
    """
    is_prod = os.getenv("ENV") == "production"
    resp.set_cookie(
        key=ORG_COOKIE_NAME,
        value=str(org_id),
        httponly=False,
        secure=is_prod,
        samesite="lax",
        domain=".neuroflowai.co.uk" if is_prod else None,
        max_age=minutes * 60,
        path="/",
    )


def clear_org_cookie(resp: Response):
    is_prod = os.getenv("ENV") == "production"
    resp.delete_cookie(
        ORG_COOKIE_NAME,
        path="/",
        domain=".neuroflowai.co.uk" if is_prod else None,
    )


# ── onboarding cookie ─────────────────────────────────────────────────────────

def set_onboarding_cookie(resp: Response, stage: str, minutes: int = 60 * 24 * 7):
    """
    Possible values:
      - branding  -> org + business info saved, resume at branding
      - complete  -> onboarding finished, allow internal app access
    """
    is_prod = os.getenv("ENV") == "production"
    resp.set_cookie(
        key=ONBOARDING_COOKIE_NAME,
        value=stage,
        httponly=False,   # proxy must read it
        secure=is_prod,
        samesite="lax",
        domain=".neuroflowai.co.uk" if is_prod else None,
        max_age=minutes * 60,
        path="/",
    )


def clear_onboarding_cookie(resp: Response):
    is_prod = os.getenv("ENV") == "production"
    resp.delete_cookie(
        ONBOARDING_COOKIE_NAME,
        path="/",
        domain=".neuroflowai.co.uk" if is_prod else None,
    )