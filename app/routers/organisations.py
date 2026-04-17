"""
app/routers/organisations.py
─────────────────────────────
Org management endpoints:
  POST   /organisations                       → create org (onboarding)
  GET    /organisations/my-orgs               → all orgs this user belongs to
  GET    /organisations/me                    → current org details + usage
  PATCH  /organisations/me                    → update org name/slug
  GET    /organisations/me/members            → list members
  POST   /organisations/me/invite             → invite member by email
  PATCH  /organisations/me/members/{user_id}  → change role
  DELETE /organisations/me/members/{user_id}  → remove member
  POST   /organisations/switch/{org_id}       → switch active org

Mount in main.py:
    from app.routers import organisations
    app.include_router(organisations.router, prefix="/organisations", tags=["organisations"])
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.services.tokens import new_token, hash_token, expires_in
from app.services.mailer import send_email, verify_link
from app.models.email_token import EmailVerificationToken
from app.services.passwords import hash_password, generate_temp_password
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.org import (
    get_current_org,
    require_role,
    get_monthly_usage,
)
from app.models.organisation import Organisation, OrganisationMember
from app.models.user import User
from app.models.brand import Brand
from app.models.platform import Platform

router = APIRouter(prefix="/organisations", tags=["organisations"])

_NF_ORG   = "nf_org"
_MAX_AGE  = 60 * 60 * 24 * 30   # 30 days


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: str
    role:  str = "member"   # admin | member | viewer


class UpdateMemberRoleRequest(BaseModel):
    role: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    return slug[:50]


def _ensure_unique_slug(db: Session, slug: str, exclude_id=None) -> str:
    base, n = slug, 1
    while True:
        q = select(Organisation).where(Organisation.slug == slug)
        if exclude_id:
            q = q.where(Organisation.id != exclude_id)
        exists = db.execute(q).scalars().first()
        if not exists:
            return slug
        slug = f"{base}-{n}"
        n += 1


def _set_org_cookie(response: JSONResponse, org_id: str) -> JSONResponse:
    """Attach the nf_org cookie so the proxy knows which org is active."""
    response.set_cookie(
        key=_NF_ORG,
        value=org_id,
        httponly=False,   # must be readable by the Next.js proxy
        samesite="lax",
        secure=False,     # set True in production (HTTPS only)
        max_age=_MAX_AGE,
    )
    return response


# ── POST /organisations ───────────────────────────────────────────────────────

@router.post("")
def create_organisation(
    payload: CreateOrgRequest,
    db:      Session = Depends(get_db),
    user             = Depends(get_current_user),
):
    """
    Create a new organisation. Requires a valid login session only — no org needed.
    Called from /onboarding (first org) or Settings > New Workspace (additional orgs).
    """
    slug = _ensure_unique_slug(db, payload.slug or _slugify(payload.name))

    org = Organisation(
        id=uuid.uuid4(),
        name=payload.name.strip(),
        slug=slug,
        plan="free",
    )
    db.add(org)
    db.flush()   # resolve org.id before FK

    db.add(OrganisationMember(
        org_id=org.id,
        user_id=user.id,
        role="owner",
    ))

    db.commit()
    db.refresh(org)

    return _set_org_cookie(
        JSONResponse({"ok": True, "organisation": org.to_dict(), "role": "owner"}),
        str(org.id),
    )


# ── GET /organisations/my-orgs ────────────────────────────────────────────────

@router.get("/my-orgs")
def list_my_organisations(
    db:   Session = Depends(get_db),
    user          = Depends(get_current_user),
):
    """
    Returns all organisations the logged-in user belongs to.
    Used to populate the org-switcher dropdown. No current org required.
    """
    rows = db.execute(
        select(Organisation, OrganisationMember)
        .join(OrganisationMember, OrganisationMember.org_id == Organisation.id)
        .where(
            OrganisationMember.user_id == user.id,
            Organisation.is_active     == True,  # noqa: E712
        )
        .order_by(OrganisationMember.joined_at.asc())
    ).all()

    return [
        {**org.to_dict(), "role": member.role}
        for org, member in rows
    ]


# ── GET /organisations/me ─────────────────────────────────────────────────────

@router.get("/me")
def get_current_organisation(
    org:  Organisation = Depends(get_current_org),
    db:   Session      = Depends(get_db),
    user               = Depends(get_current_user),
):
    draft_usage  = get_monthly_usage(db, org.id, "draft_generated")
    render_usage = get_monthly_usage(db, org.id, "video_rendered")

    brand_count = (
        db.execute(select(func.count()).select_from(Brand).where(Brand.org_id == org.id)).scalar() or 0
    )
    platform_count = (
        db.execute(select(func.count()).select_from(Platform).where(Platform.org_id == org.id)).scalar() or 0
    )
    member_count = (
        db.execute(select(func.count()).select_from(OrganisationMember).where(OrganisationMember.org_id == org.id)).scalar() or 0
    )

    return {
        **org.to_dict(),
        "role": getattr(org, "_current_role", "member"),
        "usage": {
            "drafts_this_month":  draft_usage,
            "renders_this_month": render_usage,
            "brands":             brand_count,
            "platforms":          platform_count,
            "members":            member_count,
        },
    }


# ── PATCH /organisations/me ───────────────────────────────────────────────────

@router.patch("/me")
def update_organisation(
    payload: UpdateOrgRequest,
    org:     Organisation = Depends(require_role("owner", "admin")),
    db:      Session      = Depends(get_db),
):
    if payload.name:
        org.name = payload.name.strip()
    if payload.slug:
        org.slug = _ensure_unique_slug(db, _slugify(payload.slug), exclude_id=org.id)
    org.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "organisation": org.to_dict()}


# ── GET /organisations/me/members ─────────────────────────────────────────────

@router.get("/me/members")
def list_members(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrganisationMember, User)
        .join(User, User.id == OrganisationMember.user_id)
        .where(OrganisationMember.org_id == org.id)
        .order_by(OrganisationMember.joined_at.asc())
    ).all()

    return [
        {
            "user_id":   str(member.user_id),
            "email":     user.email,
            "role":      member.role,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        }
        for member, user in rows
    ]


# ── POST /organisations/me/invite ─────────────────────────────────────────────

@router.post("/me/invite")
async def invite_member(
    payload: InviteMemberRequest,
    org:     Organisation = Depends(require_role("owner", "admin")),
    db:      Session      = Depends(get_db),
    user                  = Depends(get_current_user),
):
    if payload.role not in ("admin", "member", "viewer"):
        raise HTTPException(400, "Invalid role. Must be admin, member, or viewer")

    email = payload.email.lower().strip()

    # Check if already a registered user
    invitee = db.execute(
        select(User).where(User.email == email)
    ).scalars().first()

    newly_created = False

    if not invitee:
        # ── Create the user on the spot (same as /register) ──────────────────
        temp_password = generate_temp_password(12)
        invitee = User(
            email=email,
            first_name=email.split("@")[0],   # placeholder until they update profile
            last_name="",
            password_hash=hash_password(temp_password),
            is_email_verified=False,
        )
        db.add(invitee)
        db.flush()   # get invitee.id before FK

        # Verification token
        token     = new_token()
        t = EmailVerificationToken(
            user_id=invitee.id,
            token=hash_token(token),
            expires_at=expires_in(24 * 60),
            used_at=None,
        )
        db.add(t)
        newly_created = True

    else:
        token = None

    # Check not already a member of this org
    existing = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id  == org.id,
            OrganisationMember.user_id == invitee.id,
        )
    ).scalars().first()

    if existing:
        raise HTTPException(409, "User is already a member of this organisation")

    # Add to org
    db.add(OrganisationMember(
        org_id=org.id,
        user_id=invitee.id,
        role=payload.role,
        invited_by=user.id,
    ))
    db.commit()

    # ── Send email ────────────────────────────────────────────────────────────
    if newly_created:
        link = verify_link(token)
        await send_email(
            to=email,
            subject=f"You've been invited to {org.name} on Relvō AI",
            html=f"""
            <div style="font-family: Arial, Helvetica, sans-serif; background:#f6f7fb; padding:32px;">
              <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; padding:32px;">
                <h2 style="margin:0 0 16px; color:#111827;">You've been invited to {org.name}</h2>
                <p style="margin:0 0 16px; color:#374151; font-size:14px; line-height:1.6;">
                  <strong>{user.email}</strong> has added you to <strong>{org.name}</strong> as a <strong>{payload.role}</strong>.
                  Click below to verify your email and get started.
                </p>
                <div style="margin:24px 0;">
                  <a href="{link}" style="display:inline-block; background:#6d28d9; color:#ffffff; text-decoration:none; padding:12px 18px; border-radius:10px; font-size:14px; font-weight:700;">
                    Accept Invitation
                  </a>
                </div>
                <p style="margin:0 0 10px; color:#374151; font-size:14px;">Your temporary password:</p>
                <div style="margin:0 0 18px; padding:12px 14px; background:#f3f4f6; border-radius:10px; font-size:14px; color:#111827; font-weight:700;">
                  {temp_password}
                </div>
                <p style="margin:18px 0 0; color:#9ca3af; font-size:12px;">
                  If the button does not work:<br/>
                  <a href="{link}" style="color:#6d28d9;">{link}</a>
                </p>
              </div>
            </div>
            """,
        )
        message = f"{email} was registered and added to {org.name} as {payload.role}. Invite email sent."
    else:
        # Existing user — just notify them
        await send_email(
            to=email,
            subject=f"You've been added to {org.name} on Relvō AI",
            html=f"""
            <div style="font-family: Arial, Helvetica, sans-serif; background:#f6f7fb; padding:32px;">
              <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; padding:32px;">
                <h2 style="margin:0 0 16px; color:#111827;">You've been added to {org.name}</h2>
                <p style="margin:0 0 16px; color:#374151; font-size:14px; line-height:1.6;">
                  <strong>{user.email}</strong> has added you to <strong>{org.name}</strong> as a <strong>{payload.role}</strong>.
                  Log in to Relvō to switch to this workspace.
                </p>
                <div style="margin:24px 0;">
                  <a href="{verify_link('').rsplit('/', 1)[0].replace('/verify-email', '')}/auth/login" style="display:inline-block; background:#6d28d9; color:#ffffff; text-decoration:none; padding:12px 18px; border-radius:10px; font-size:14px; font-weight:700;">
                    Go to Relvō
                  </a>
                </div>
              </div>
            </div>
            """,
        )
        message = f"{email} added to {org.name} as {payload.role}."

    return {"ok": True, "message": message}


# ── PATCH /organisations/me/members/{target_user_id} ─────────────────────────

@router.patch("/me/members/{target_user_id}")
def update_member_role(
    target_user_id: str,
    payload:        UpdateMemberRoleRequest,
    org:            Organisation = Depends(require_role("owner", "admin")),
    db:             Session      = Depends(get_db),
    user                         = Depends(get_current_user),
):
    if payload.role not in ("admin", "member", "viewer"):
        raise HTTPException(400, "Invalid role")

    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id  == org.id,
            OrganisationMember.user_id == uuid.UUID(target_user_id),
        )
    ).scalars().first()

    if not member:
        raise HTTPException(404, "Member not found")
    if member.role == "owner" and str(user.id) != target_user_id:
        raise HTTPException(403, "Cannot change the owner's role")

    member.role = payload.role
    db.commit()
    return {"ok": True}


# ── DELETE /organisations/me/members/{target_user_id} ────────────────────────

@router.delete("/me/members/{target_user_id}")
def remove_member(
    target_user_id: str,
    org:            Organisation = Depends(require_role("owner", "admin")),
    db:             Session      = Depends(get_db),
):
    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id  == org.id,
            OrganisationMember.user_id == uuid.UUID(target_user_id),
        )
    ).scalars().first()

    if not member:
        raise HTTPException(404, "Member not found")
    if member.role == "owner":
        raise HTTPException(403, "Cannot remove the organisation owner")

    db.delete(member)
    db.commit()
    return {"ok": True}


# ── POST /organisations/switch/{org_id} ──────────────────────────────────────

@router.post("/switch/{org_id}")
def switch_organisation(
    org_id: str,
    db:     Session = Depends(get_db),
    user            = Depends(get_current_user),
):
    """
    Switch the active org for this session by updating the nf_org cookie.
    No current org required — only a valid login session.
    """
    oid = uuid.UUID(org_id)

    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id  == oid,
            OrganisationMember.user_id == user.id,
        )
    ).scalars().first()

    if not member:
        raise HTTPException(403, "You are not a member of that organisation")

    return _set_org_cookie(
        JSONResponse({"ok": True, "org_id": str(oid), "role": member.role}),
        str(oid),
    )

@router.delete("/me", status_code=204)
def delete_organisation(
    org  = Depends(require_role("owner")),
    db:  Session = Depends(get_db),
):
    # Delete all org data then the org itself
    # CASCADE on FK handles most of it
    db.delete(org)
    db.commit()