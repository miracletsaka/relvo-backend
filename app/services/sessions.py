"""
Patch for app/utils/sessions.py
────────────────────────────────
Add set_org_cookie() and clear_org_cookie() alongside your existing
set_session_cookie() and clear_session_cookie().

FastAPI sets the nf_org cookie at two points:
  1. Login  — if the user already belongs to an org
  2. POST /organisations — when they create their first org

The proxy reads nf_org to know whether to redirect to /onboarding.
No DB or API call needed in the proxy — just a cookie read.
"""

import hashlib
import os
import secrets
from datetime import timedelta
from fastapi import Response

from .tokens import utcnow

COOKIE_NAME     = "nf_session"
ORG_COOKIE_NAME = "nf_org"        # ← NEW


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
    resp.delete_cookie(COOKIE_NAME, path="/")


# ── NEW: org cookie ───────────────────────────────────────────────────────────

def set_org_cookie(resp: Response, org_id: str, minutes: int = 60 * 24 * 7):
    """
    Set the nf_org cookie so the Next.js proxy can read it without
    making an API call. NOT httponly — proxy needs to read it.
    Value is just the org UUID (not sensitive — org_id is not a secret).
    """
    is_prod = os.getenv("ENV") == "production"
    resp.set_cookie(
        key=ORG_COOKIE_NAME,
        value=str(org_id),
        httponly=False,      # proxy reads this — must NOT be httponly
        secure=is_prod,
        samesite="lax",
        domain=".neuroflowai.co.uk" if is_prod else None,
        max_age=minutes * 60,
        path="/",
    )


def clear_org_cookie(resp: Response):
    resp.delete_cookie(ORG_COOKIE_NAME, path="/")