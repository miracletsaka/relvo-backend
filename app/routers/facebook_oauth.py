from __future__ import annotations

import os
import secrets
from datetime import timedelta
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.org import get_current_org
from app.models.facebook_connection import FacebookConnection
from app.models.facebook_oauth_state import FacebookOAuthState
from app.models.facebook_page import FacebookPage
from app.models.organisation import Organisation
from app.models.user import User
from app.services.tokens import utcnow

router = APIRouter(prefix="/facebook", tags=["facebook"])

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
GRAPH_VERSION = "v19.0"

SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "business_management",
]


def _require_env():
    missing = [
        name
        for name, value in {
            "FACEBOOK_CLIENT_ID": FACEBOOK_CLIENT_ID,
            "FACEBOOK_CLIENT_SECRET": FACEBOOK_CLIENT_SECRET,
            "FACEBOOK_REDIRECT_URI": FACEBOOK_REDIRECT_URI,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing Facebook OAuth env vars: {', '.join(missing)}")


@router.get("/connect")
def connect_facebook(
    org: Organisation = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_env()
    state = secrets.token_urlsafe(32)
    db.add(FacebookOAuthState(state=state, org_id=org.id, user_id=user.id, expires_at=utcnow() + timedelta(minutes=15)))
    db.commit()
    auth_url = (
        f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
        f"?client_id={FACEBOOK_CLIENT_ID}"
        f"&redirect_uri={FACEBOOK_REDIRECT_URI}"
        f"&scope={','.join(SCOPES)}"
        f"&response_type=code"
        f"&state={state}"
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
def facebook_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    _require_env()
    if error:
        raise HTTPException(status_code=400, detail=error_description or error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    saved_state = db.execute(select(FacebookOAuthState).where(FacebookOAuthState.state == state)).scalars().first()
    if not saved_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if saved_state.expires_at < utcnow():
        db.delete(saved_state)
        db.commit()
        raise HTTPException(status_code=400, detail="OAuth state expired")

    token_res = requests.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token",
        params={"client_id": FACEBOOK_CLIENT_ID, "client_secret": FACEBOOK_CLIENT_SECRET, "redirect_uri": FACEBOOK_REDIRECT_URI, "code": code},
        timeout=30,
    )
    token_data = token_res.json()
    if token_res.status_code >= 400:
        raise HTTPException(status_code=400, detail=token_data)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get Facebook access token")

    me_res = requests.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/me",
        params={"fields": "id,name", "access_token": access_token},
        timeout=30,
    )
    me_data = me_res.json()
    if me_res.status_code >= 400:
        raise HTTPException(status_code=400, detail=me_data)

    connection = db.execute(select(FacebookConnection).where(FacebookConnection.org_id == saved_state.org_id)).scalars().first()
    if not connection:
        connection = FacebookConnection(id=uuid4(), org_id=saved_state.org_id, user_id=saved_state.user_id)
        db.add(connection)
    connection.facebook_user_id = me_data.get("id")
    connection.facebook_name = me_data.get("name")
    connection.access_token = access_token
    connection.scopes = ",".join(SCOPES)
    db.commit()

    pages_res = requests.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/me/accounts",
        params={"fields": "id,name,category,access_token", "access_token": access_token},
        timeout=30,
    )
    pages_payload = pages_res.json()
    if pages_res.status_code >= 400:
        raise HTTPException(status_code=400, detail=pages_payload)

    for page in pages_payload.get("data", []):
        page_id = page.get("id")
        page_token = page.get("access_token")
        page_name = page.get("name")
        if not page_id or not page_token or not page_name:
            continue
        existing = db.execute(
            select(FacebookPage).where(FacebookPage.org_id == saved_state.org_id, FacebookPage.facebook_page_id == page_id)
        ).scalars().first()
        if not existing:
            existing = FacebookPage(id=uuid4(), org_id=saved_state.org_id, facebook_page_id=page_id)
            db.add(existing)
        existing.name = page_name
        existing.category = page.get("category")
        existing.access_token = page_token

    db.delete(saved_state)
    db.commit()
    return RedirectResponse(f"{FRONTEND_URL}/dashboard/integrations/facebook")


@router.get("/status")
def facebook_status(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    connection = db.execute(select(FacebookConnection).where(FacebookConnection.org_id == org.id)).scalars().first()
    if not connection:
        return {"connected": False, "pages": []}
    pages = db.execute(select(FacebookPage).where(FacebookPage.org_id == org.id)).scalars().all()
    return {
        "connected": True,
        "facebook_name": connection.facebook_name,
        "facebook_user_id": connection.facebook_user_id,
        "scopes": connection.scopes,
        "pages": [
            {"id": str(page.id), "facebook_page_id": page.facebook_page_id, "name": page.name, "category": page.category, "is_selected": page.is_selected}
            for page in pages
        ],
    }


@router.post("/select-page/{page_id}")
def select_facebook_page(page_id: str, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    pages = db.execute(select(FacebookPage).where(FacebookPage.org_id == org.id)).scalars().all()
    found = False
    for page in pages:
        is_target = str(page.id) == page_id or page.facebook_page_id == page_id
        page.is_selected = is_target
        if is_target:
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    db.commit()
    return {"success": True}


@router.post("/disconnect")
def disconnect_facebook(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    pages = db.execute(select(FacebookPage).where(FacebookPage.org_id == org.id)).scalars().all()
    for page in pages:
        db.delete(page)
    connection = db.execute(select(FacebookConnection).where(FacebookConnection.org_id == org.id)).scalars().first()
    if connection:
        db.delete(connection)
    db.commit()
    return {"success": True}
