
import hashlib
import secrets

from fastapi import Response

COOKIE_NAME = "nf_session"
ORG_COOKIE_NAME = "nf_org"
ONBOARDING_COOKIE_NAME = "nf_onboarding"

# Production runs on Render over HTTPS.
# Cross-site requests between Vercel and Render require SameSite=None.
COOKIE_SECURE = True
COOKIE_SAMESITE = "none"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_cookie(
    resp: Response,
    key: str,
    value: str,
    *,
    httponly: bool,
    minutes: int = 60 * 24 * 7,
):
    resp.set_cookie(
        key=key,
        value=value,
        httponly=httponly,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=minutes * 60,
        path="/",
    )


def _clear_cookie(resp: Response, key: str):
    resp.delete_cookie(
        key=key,
        path="/",
        secure=COOKIE_SECURE,
        httponly=False,
        samesite=COOKIE_SAMESITE,
    )


def set_session_cookie(
    resp: Response,
    token: str,
    minutes: int = 60 * 24 * 7,
):
    _set_cookie(
        resp,
        COOKIE_NAME,
        token,
        httponly=True,
        minutes=minutes,
    )


def clear_session_cookie(resp: Response):
    _clear_cookie(resp, COOKIE_NAME)


# Organisation cookie
def set_org_cookie(
    resp: Response,
    org_id: str,
    minutes: int = 60 * 24 * 7,
):
    _set_cookie(
        resp,
        ORG_COOKIE_NAME,
        str(org_id),
        httponly=False,
        minutes=minutes,
    )


def clear_org_cookie(resp: Response):
    _clear_cookie(resp, ORG_COOKIE_NAME)


# Onboarding cookie
def set_onboarding_cookie(
    resp: Response,
    stage: str,
    minutes: int = 60 * 24 * 7,
):
    _set_cookie(
        resp,
        ONBOARDING_COOKIE_NAME,
        stage,
        httponly=False,
        minutes=minutes,
    )


def clear_onboarding_cookie(resp: Response):
    _clear_cookie(resp, ONBOARDING_COOKIE_NAME)
