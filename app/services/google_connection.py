"""
backend/app/services/google_connection.py
──────────────────────────────────────
Google token encryption, refresh, and service builders.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi import HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import text
from sqlalchemy.orm import Session

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FERNET_KEY = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY", "")


def _fernet() -> Fernet:
    if not FERNET_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_TOKEN_ENCRYPTION_KEY missing")
    return Fernet(FERNET_KEY.encode())


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token: str | None) -> str | None:
    if not token:
        return None
    return _fernet().decrypt(token.encode()).decode()


def _get_connection(db: Session, org_id):
    row = db.execute(
        text("""
            SELECT id, access_token_encrypted, refresh_token_encrypted, scopes, expires_at
            FROM google_connections
            WHERE org_id = :org_id
            ORDER BY updated_at DESC
            LIMIT 1
        """),
        {"org_id": str(org_id)},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=400, detail="Google is not connected for this organisation")

    return row


def _refresh_access_token(db: Session, connection) -> str:
    refresh_token = decrypt_token(connection["refresh_token_encrypted"])

    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing Google refresh token. Reconnect Google.")

    import httpx

    res = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )

    if res.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Google token refresh failed: {res.text}")

    data = res.json()
    access_token = data.get("access_token")
    expires_in = int(data.get("expires_in") or 3600)

    if not access_token:
        raise HTTPException(status_code=400, detail="Google did not return refreshed access token")

    db.execute(
        text("""
            UPDATE google_connections
            SET access_token_encrypted = :access_token,
                expires_at = :expires_at,
                updated_at = now()
            WHERE id = :id
        """),
        {
            "id": str(connection["id"]),
            "access_token": encrypt_token(access_token),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        },
    )
    db.commit()

    return access_token


def get_google_credentials(db: Session, org_id) -> Credentials:
    connection = _get_connection(db, org_id)

    access_token = decrypt_token(connection["access_token_encrypted"])
    refresh_token = decrypt_token(connection["refresh_token_encrypted"])

    expires_at = connection["expires_at"]
    now = datetime.now(timezone.utc)

    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not access_token or not expires_at or expires_at <= now + timedelta(minutes=3):
        access_token = _refresh_access_token(db, connection)

    scopes = str(connection["scopes"] or "").split()

    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=scopes,
    )


def get_drive_service(db: Session, org_id):
    creds = get_google_credentials(db, org_id)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_docs_service(db: Session, org_id):
    creds = get_google_credentials(db, org_id)
    return build("docs", "v1", credentials=creds, cache_discovery=False)
