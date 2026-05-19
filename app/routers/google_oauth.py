"""
backend/app/routers/google_oauth.py
──────────────────────────────────
Org-level Google OAuth connection.

Required env:
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/google/callback
GOOGLE_TOKEN_ENCRYPTION_KEY=32-byte-fernet-key

Install:
pip install google-auth google-auth-oauthlib google-api-python-client cryptography httpx
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.org import get_current_org
from app.services.google_connection import encrypt_token

router = APIRouter(prefix="/google", tags=["Google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents",
]

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
TOKEN_ENCRYPTION_KEY = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY")


@router.get("/status")
def google_status(
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    row = db.execute(
        text("""
            SELECT google_email, scopes, expires_at, created_at, updated_at
            FROM google_connections
            WHERE org_id = :org_id
            ORDER BY updated_at DESC
            LIMIT 1
        """),
        {"org_id": str(org.id)},
    ).mappings().first()

    if not row:
        return {"connected": False}

    return {
        "connected": True,
        "google_email": row["google_email"],
        "scopes": row["scopes"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/connect")
def connect_google(
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    if not CLIENT_ID or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth env vars missing")

    state = secrets.token_urlsafe(32)

    db.execute(
        text("""
            INSERT INTO google_oauth_states (state, org_id, user_id, expires_at)
            VALUES (:state, :org_id, :user_id, :expires_at)
        """),
        {
            "state": state,
            "org_id": str(org.id),
            "user_id": str(user.id),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
    )
    db.commit()

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }

    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth env vars missing")

    state_row = db.execute(
        text("""
            SELECT org_id, user_id
            FROM google_oauth_states
            WHERE state = :state AND expires_at > now()
            LIMIT 1
        """),
        {"state": state},
    ).mappings().first()

    if not state_row:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    import httpx

    async with httpx.AsyncClient(timeout=20) as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_res.status_code >= 400:
        raise HTTPException(status_code=400, detail=token_res.text)

    token_data = token_res.json()

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = int(token_data.get("expires_in") or 3600)
    scopes = token_data.get("scope") or " ".join(SCOPES)

    if not access_token:
        raise HTTPException(status_code=400, detail="Google did not return an access token")

    google_email = None

    async with httpx.AsyncClient(timeout=20) as client:
        info_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if info_res.status_code < 400:
        google_email = info_res.json().get("email")

    existing = db.execute(
        text("""
            SELECT id
            FROM google_connections
            WHERE org_id = :org_id
            LIMIT 1
        """),
        {"org_id": str(state_row["org_id"])},
    ).mappings().first()

    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if existing:
        db.execute(
            text("""
                UPDATE google_connections
                SET google_email = :google_email,
                    access_token_encrypted = :access_token,
                    refresh_token_encrypted = COALESCE(:refresh_token, refresh_token_encrypted),
                    scopes = :scopes,
                    expires_at = :expires_at,
                    updated_at = now()
                WHERE id = :id
            """),
            {
                "id": str(existing["id"]),
                "google_email": google_email,
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "scopes": scopes,
                "expires_at": expires_at,
            },
        )
    else:
        db.execute(
            text("""
                INSERT INTO google_connections
                    (org_id, connected_by_user_id, google_email, access_token_encrypted,
                     refresh_token_encrypted, scopes, expires_at)
                VALUES
                    (:org_id, :user_id, :google_email, :access_token,
                     :refresh_token, :scopes, :expires_at)
            """),
            {
                "org_id": str(state_row["org_id"]),
                "user_id": str(state_row["user_id"]),
                "google_email": google_email,
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "scopes": scopes,
                "expires_at": expires_at,
            },
        )

    db.execute(text("DELETE FROM google_oauth_states WHERE state = :state"), {"state": state})
    db.commit()

    return RedirectResponse("http://localhost:3000/dashboard/integrations/google?google=connected")


@router.post("/disconnect")
def disconnect_google(
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    db.execute(
        text("DELETE FROM google_connections WHERE org_id = :org_id"),
        {"org_id": str(org.id)},
    )
    db.commit()

    return {"ok": True}
