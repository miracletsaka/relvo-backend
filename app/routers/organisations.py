"""
app/routers/organisations.py
─────────────────────────────
Org management endpoints:
  POST   /organisations                       → create org (onboarding)
  GET    /organisations/my-orgs               → all orgs this user belongs to
  GET    /organisations/me                    → current org details + usage
  PATCH  /organisations/me                    → update org name/slug/logo_url
  GET    /organisations/me/members            → list members
  POST   /organisations/me/invite             → invite member by email
  PATCH  /organisations/me/members/{user_id}  → change role
  DELETE /organisations/me/members/{user_id}  → remove member
  POST   /organisations/switch/{org_id}       → switch active org
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
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
from app.services.sessions import set_org_cookie
from app.models.org_profile import OrgBusinessInfo

router = APIRouter(prefix="/organisations", tags=["organisations"])

_NF_ORG   = "nf_org"
_MAX_AGE  = 60 * 60 * 24 * 30   # 30 days


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class UpdateOrgRequest(BaseModel):
    name:     Optional[str] = None
    slug:     Optional[str] = None
    logo_url: Optional[str] = None   # ← NEW: organisation logo


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
    response.set_cookie(
        key=_NF_ORG,
        value=org_id,
        httponly=False,
        samesite="lax",
        secure=False,
        max_age=_MAX_AGE,
    )
    return response


# ── POST /organisations ───────────────────────────────────────────────────────

@router.post("")
def create_organisation(
    payload: CreateOrgRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
    resp: Response = None,
):
    slug = _ensure_unique_slug(db, payload.slug or _slugify(payload.name))

    org = Organisation(
        id=uuid.uuid4(),
        name=payload.name.strip(),
        slug=slug,
        plan="free",
    )
    db.add(org)
    db.flush()

    db.add(OrganisationMember(
        org_id=org.id,
        user_id=user.id,
        role="owner",
    ))

    db.commit()
    db.refresh(org)

    set_org_cookie(resp, str(org.id))

    return {"ok": True, "organisation": org.to_dict(), "role": "owner"}


# ── GET /organisations/my-orgs ────────────────────────────────────────────────

@router.get("/my-orgs")
def list_my_organisations(
    db:   Session = Depends(get_db),
    user          = Depends(get_current_user),
):
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

@router.get("/me/business-info")
def get_org_business_info(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    """
    Returns org_business_info row for the current org.
    Sidebar uses the social URL fields to build dynamic external nav links.
    """
    row = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == org.id)
    ).scalars().first()
 
    if not row:
        return {}   # no business info yet — return empty dict, not 404
    
    print("Org business info found:", row)  # debug log
 
    return {
        "business_type":   row.business_type,
        "founded_year":    row.founded_year,
        "company_size":    row.company_size,
        "website":         row.website,
        "address":         row.address,
        "tagline":         row.tagline,
        "description":     row.description,
        "email_primary":   row.email_primary,
        "email_support":   row.email_support,
        "phone_primary":   row.phone_primary,
        "phone_secondary": row.phone_secondary,
        "whatsapp":        row.whatsapp,
        "country":         row.country,
        "city":            row.city,
        "state_province":  row.state_province,
        "postal_code":     row.postal_code,
        "map_url":         row.map_url,
        # Social URLs — used by sidebar quick links
        "facebook_url":    row.facebook_url,
        "instagram_url":   row.instagram_url,
        "linkedin_url":    row.linkedin_url,
        "twitter_url":     row.twitter_url,
        "tiktok_url":      row.tiktok_url,
        "youtube_url":     row.youtube_url,
        "registration_no": row.registration_no,
        "vat_number":      row.vat_number,
    }

# ── PATCH /organisations/me ───────────────────────────────────────────────────

@router.patch("/me")
def update_organisation(
    payload: UpdateOrgRequest,
    org:     Organisation = Depends(require_role("owner", "admin")),
    db:      Session      = Depends(get_db),
):
    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.slug is not None:
        org.slug = _ensure_unique_slug(db, _slugify(payload.slug), exclude_id=org.id)
    if payload.logo_url is not None:
        # Empty string clears the logo; any other string sets it
        org.logo_url = payload.logo_url if payload.logo_url.strip() else None

    org.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(org)
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

    invitee = db.execute(
        select(User).where(User.email == email)
    ).scalars().first()

    newly_created = False

    if not invitee:
        temp_password = generate_temp_password(12)
        invitee = User(
            email=email,
            first_name=email.split("@")[0],
            last_name="",
            password_hash=hash_password(temp_password),
            is_email_verified=False,
        )
        db.add(invitee)
        db.flush()

        token = new_token()
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

    existing = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id  == org.id,
            OrganisationMember.user_id == invitee.id,
        )
    ).scalars().first()

    if existing:
        raise HTTPException(409, "User is already a member of this organisation")

    db.add(OrganisationMember(
        org_id=org.id,
        user_id=invitee.id,
        role=payload.role,
        invited_by=user.id,
    ))
    db.commit()

    if newly_created:
        link = verify_link(token)
        await send_email(
            to=email,
            subject=f"You've been invited to {org.name} on Relvo",
            html=f"""
            <div style="font-family: Arial, Helvetica, sans-serif; background:#f6f7fb; padding:32px;">
              <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; padding:32px;">
                <h2 style="margin:0 0 16px; color:#111827;">You've been invited to {org.name}</h2>
                <p style="margin:0 0 16px; color:#374151; font-size:14px; line-height:1.6;">
                  <strong>{user.email}</strong> has added you to <strong>{org.name}</strong> as a <strong>{payload.role}</strong>.
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
              </div>
            </div>
            """,
        )
        message = f"{email} was registered and added to {org.name} as {payload.role}. Invite email sent."
    else:
        await send_email(
            to=email,
            subject=f"You've been added to {org.name} on Relvo",
            html=f"""
            <div style="font-family: Arial, Helvetica, sans-serif; background:#f6f7fb; padding:32px;">
              <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; padding:32px;">
                <h2 style="margin:0 0 16px; color:#111827;">You've been added to {org.name}</h2>
                <p style="margin:0 0 16px; color:#374151; font-size:14px; line-height:1.6;">
                  <strong>{user.email}</strong> has added you to <strong>{org.name}</strong> as a <strong>{payload.role}</strong>.
                </p>
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
    db.delete(org)
    db.commit()