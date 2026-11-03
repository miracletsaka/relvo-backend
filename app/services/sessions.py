
import hashlib
import os
import secrets

from fastapi import Response

COOKIE_NAME = "nf_session"
ORG_COOKIE_NAME = "nf_org"
ONBOARDING_COOKIE_NAME = "nf_onboarding"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cookie_settings() -> dict:
    is_prod = os.getenv("ENV", "").lower() == "production"

    return {
        "secure": is_prod,
        "samesite": "none" if is_prod else "lax",
        # Do not set a domain.
        # The browser will associate the cookie with the Render backend.
    }


def set_session_cookie(resp: Response, token: str, minutes: int = 60 * 24 * 7):
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=minutes * 60,
        path="/",
        **_cookie_settings(),
    )


def clear_session_cookie(resp: Response):
    resp.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        **_cookie_settings(),
    )


def set_org_cookie(resp: Response, org_id: str, minutes: int = 60 * 24 * 7):
    resp.set_cookie(
        key=ORG_COOKIE_NAME,
        value=str(org_id),
        httponly=False,
        max_age=minutes * 60,
        path="/",
        **_cookie_settings(),
    )


def clear_org_cookie(resp: Response):
    resp.delete_cookie(
        key=ORG_COOKIE_NAME,
        path="/",
        **_cookie_settings(),
    )


def set_onboarding_cookie(
    resp: Response,
    stage: str,
    minutes: int = 60 * 24 * 7,
):
    resp.set_cookie(
        key=ONBOARDING_COOKIE_NAME,
        value=stage,
        httponly=False,
        max_age=minutes * 60,
        path="/",
        **_cookie_settings(),
    )


def clear_onboarding_cookie(resp: Response):
    resp.delete_cookie(
        key=ONBOARDING_COOKIE_NAME,
        path="/",
        **_cookie_settings(),
    )
