"""
app/routers/public_profile.py
──────────────────────────────
Public business profile + secure email-verified reviews + org images.

Public (no auth):
  GET  /public/biz/{slug}
  POST /public/biz/{slug}/request-review
  GET  /public/biz/{slug}/review/{token}
  POST /public/biz/{slug}/review/{token}

Private (auth required):
  GET    /org-images
  POST   /org-images
  DELETE /org-images/{image_id}
  POST   /review-requests/send
  GET    /review-requests
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.org import get_current_org, require_role
from app.models.organisation import Organisation
from app.models.org_profile import (
    OrgBusinessInfo, OrgReview, OrgSponsor,
    OrgAccreditation, OrgOffer, OrgCampaignGoal,
)
from app.models.org_images import OrgImage, ReviewToken, ReviewRequest
from app.services.mailer import send_email

router = APIRouter(tags=["public"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def _new_token() -> str:
    return secrets.token_urlsafe(48)

def _review_link(slug: str, token: str, base_url: str) -> str:
    return f"{base_url}/business/{slug}/review/{token}"

def _get_org(db: Session, slug: str) -> Organisation:
    org = db.execute(
        select(Organisation).where(
            Organisation.slug == slug.lower().strip(),
            Organisation.is_active == True,  # noqa: E712
        )
    ).scalars().first()
    if not org:
        raise HTTPException(404, "Business not found")
    return org

def _frontend_url(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    return base.replace(":8000", ":3000")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReviewEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)

class ReviewSubmit(BaseModel):
    author_name: str   = Field(..., min_length=1, max_length=200)
    rating:      float = Field(..., ge=1.0, le=5.0)
    body:        Optional[str] = Field(None, max_length=2000)

class OrgImageIn(BaseModel):
    type:       str           = "gallery"
    url:        str
    caption:    Optional[str] = None
    sort_order: int           = 0

class ReviewRequestIn(BaseModel):
    email:   str = Field(..., min_length=3, max_length=320)
    message: Optional[str] = None


# ── Email helpers ─────────────────────────────────────────────────────────────

def _email_html(org_name: str, link: str, intro: str, note_html: str = "") -> str:
    return f"""
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;background:#f5f5f0;padding:40px 20px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:40px;">
      <h1 style="margin:0 0 6px;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">{org_name}</h1>
      <p style="margin:0;color:rgba(255,255,255,0.5);font-size:13px;">Verified Review Invitation</p>
    </div>
    <div style="padding:36px 40px;">
      <p style="color:#374151;font-size:15px;line-height:1.75;margin:0 0 20px;">{intro}</p>
      {note_html}
      <div style="text-align:center;margin:32px 0;">
        <a href="{link}" style="display:inline-block;background:#111827;color:#fff;text-decoration:none;padding:14px 36px;border-radius:12px;font-size:15px;font-weight:700;">
          Share My Experience →
        </a>
      </div>
      <div style="background:#f9fafb;border-radius:12px;padding:14px 18px;">
        <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.7;">
          🔒 This link is unique to you and expires in 48 hours.<br>
          Each email address can only leave one review per business.
        </p>
      </div>
      <p style="margin:24px 0 0;color:#9ca3af;font-size:12px;">
        Link not working? Copy this URL:<br>
        <a href="{link}" style="color:#6366f1;word-break:break-all;">{link}</a>
      </p>
    </div>
    <div style="border-top:1px solid #f3f4f6;padding:18px 40px;text-align:center;">
      <p style="margin:0;color:#d1d5db;font-size:11px;">Powered by NeuroFlow AI · Verified Reviews</p>
    </div>
  </div>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/public/biz/{slug}")
def get_public_profile(slug: str, db: Session = Depends(get_db)):
    org = _get_org(db, slug)
    oid = org.id

    biz = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == oid)
    ).scalars().first()

    reviews = db.execute(
        select(OrgReview).where(OrgReview.org_id == oid)
        .order_by(
            OrgReview.is_featured.desc(),
            OrgReview.created_at.desc(),
        )
    ).scalars().all()

    avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None

    sponsors = db.execute(
        select(OrgSponsor)
        .where(OrgSponsor.org_id == oid, OrgSponsor.is_active == True)  # noqa
        .order_by(OrgSponsor.sort_order.asc())
    ).scalars().all()

    accreditations = db.execute(
        select(OrgAccreditation)
        .where(OrgAccreditation.org_id == oid, OrgAccreditation.is_active == True)  # noqa
        .order_by(OrgAccreditation.year.desc().nulls_last())
    ).scalars().all()

    from datetime import date
    offers_all = db.execute(
        select(OrgOffer)
        .where(OrgOffer.org_id == oid, OrgOffer.is_active == True)  # noqa
        .order_by(OrgOffer.created_at.desc())
    ).scalars().all()
    offers = [o for o in offers_all if o.expires_at is None or o.expires_at >= date.today()]

    goals = db.execute(
        select(OrgCampaignGoal)
        .where(OrgCampaignGoal.org_id == oid, OrgCampaignGoal.is_active == True)  # noqa
        .order_by(OrgCampaignGoal.sort_order.asc())
    ).scalars().all()

    images = db.execute(
        select(OrgImage)
        .where(OrgImage.org_id == oid, OrgImage.is_active == True)  # noqa
        .order_by(OrgImage.sort_order.asc(), OrgImage.created_at.asc())
    ).scalars().all()

    def _safe_review(r: OrgReview) -> dict:
        d = r.to_dict()
        d.pop("reviewer_email", None)
        return d

    return {
        "org":            {"id": str(org.id), "name": org.name, "slug": org.slug},
        "business_info":  biz.to_dict() if biz else None,
        "cover_image":    next((i.to_dict() for i in images if i.type == "cover"),   None),
        "profile_image":  next((i.to_dict() for i in images if i.type == "profile"), None),
        "gallery":        [i.to_dict() for i in images if i.type == "gallery"],
        "rating_summary": {
            "average":        avg,
            "total_reviews":  len(reviews),
            "verified_count": sum(1 for r in reviews),
        },
        "reviews":        [_safe_review(r) for r in reviews],
        "sponsors":       [s.to_dict() for s in sponsors],
        "accreditations": [a.to_dict() for a in accreditations],
        "offers":         [o.to_dict() for o in offers],
        "campaign_goals": [g.to_dict() for g in goals],
    }


@router.post("/public/biz/{slug}/request-review")
async def request_review_token(
    slug:    str,
    payload: ReviewEmailRequest,
    request: Request,
    db:      Session = Depends(get_db),
):
    org   = _get_org(db, slug)
    email = payload.email.lower().strip()

    existing = db.execute(
        select(ReviewToken).where(
            ReviewToken.org_id == org.id,
            ReviewToken.email  == email,
        )
    ).scalars().first()

    if existing and existing.used_at:
        raise HTTPException(409, detail={
            "code":    "ALREADY_REVIEWED",
            "message": "You have already submitted a review for this business.",
        })

    raw        = _new_token()
    token_hash = _hash_token(raw)
    expires    = datetime.now(timezone.utc) + timedelta(hours=48)

    if existing:
        existing.token_hash = token_hash
        existing.expires_at = expires
        existing.used_at    = None
    else:
        db.add(ReviewToken(
            id=uuid.uuid4(), org_id=org.id, email=email,
            token_hash=token_hash, expires_at=expires,
        ))
    db.commit()

    link  = _review_link(org.slug, raw, _frontend_url(request))
    intro = f"You've been invited to share your experience with <strong>{org.name}</strong>. Click below to leave your verified review."

    await send_email(
        to=email,
        subject=f"Leave a review for {org.name}",
        html=_email_html(org.name, link, intro),
    )
    return {"ok": True, "message": "Check your inbox — review link sent."}


@router.get("/public/biz/{slug}/review/{token}")
def validate_review_token(slug: str, token: str, db: Session = Depends(get_db)):
    org  = _get_org(db, slug)
    now  = datetime.now(timezone.utc)
    rt   = db.execute(
        select(ReviewToken).where(
            ReviewToken.org_id     == org.id,
            ReviewToken.token_hash == _hash_token(token),
        )
    ).scalars().first()

    if not rt:
        raise HTTPException(404, {"code": "INVALID_TOKEN", "message": "This review link is invalid."})
    if rt.used_at:
        raise HTTPException(409, {"code": "ALREADY_USED",  "message": "This link has already been used."})
    if rt.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(410, {"code": "EXPIRED",       "message": "This link has expired. Please request a new one."})

    biz = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == org.id)
    ).scalars().first()

    images = db.execute(
        select(OrgImage).where(OrgImage.org_id == org.id, OrgImage.is_active == True)  # noqa
    ).scalars().all()

    return {
        "ok":    True,
        "email": rt.email,
        "org":   {"name": org.name, "slug": org.slug},
        "business_info":  biz.to_dict() if biz else None,
        "profile_image":  next((i.to_dict() for i in images if i.type == "profile"), None),
    }


@router.post("/public/biz/{slug}/review/{token}", status_code=201)
def submit_verified_review(
    slug:    str,
    token:   str,
    payload: ReviewSubmit,
    db:      Session = Depends(get_db),
):
    org  = _get_org(db, slug)
    now  = datetime.now(timezone.utc)
    rt   = db.execute(
        select(ReviewToken).where(
            ReviewToken.org_id     == org.id,
            ReviewToken.token_hash == _hash_token(token),
        )
    ).scalars().first()

    if not rt:
        raise HTTPException(404, {"code": "INVALID_TOKEN", "message": "Invalid review link."})
    if rt.used_at:
        raise HTTPException(409, {"code": "ALREADY_USED",  "message": "Already submitted."})
    if rt.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(410, {"code": "EXPIRED",       "message": "Link expired."})

    rt.used_at = now

    review = OrgReview(
        id=uuid.uuid4(),
        org_id=org.id,
        author_name=payload.author_name.strip(),
        rating=round(payload.rating * 2) / 2,
        review_date=now,
        body=payload.body.strip() if payload.body else None,
        source="Verified",
        is_featured=False,
        reviewer_email=rt.email,
    )
    db.add(review)

    rr = db.execute(
        select(ReviewRequest).where(
            ReviewRequest.org_id == org.id,
            ReviewRequest.email  == rt.email,
        )
    ).scalars().first()
    if rr:
        rr.reviewed_at = now

    db.commit()
    db.refresh(review)

    result = review.to_dict()
    result.pop("reviewer_email", None)
    return {"ok": True, "review": result}


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/org-images")
def list_org_images(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    images = db.execute(
        select(OrgImage).where(OrgImage.org_id == org.id)
        .order_by(OrgImage.type.asc(), OrgImage.sort_order.asc())
    ).scalars().all()
    return [i.to_dict() for i in images]


@router.post("/org-images", status_code=201)
def add_org_image(
    payload: OrgImageIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    if payload.type not in ("cover", "profile", "gallery"):
        raise HTTPException(400, "type must be cover, profile, or gallery")

    if payload.type in ("cover", "profile"):
        old = db.execute(
            select(OrgImage).where(OrgImage.org_id == org.id, OrgImage.type == payload.type)
        ).scalars().all()
        for o in old:
            db.delete(o)

    img = OrgImage(
        id=uuid.uuid4(), org_id=org.id,
        type=payload.type, url=payload.url.strip(),
        caption=payload.caption, sort_order=payload.sort_order,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img.to_dict()


@router.delete("/org-images/{image_id}", status_code=204)
def delete_org_image(
    image_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    try:
        uid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(400, "Invalid ID")
    img = db.execute(
        select(OrgImage).where(OrgImage.id == uid, OrgImage.org_id == org.id)
    ).scalars().first()
    if not img:
        raise HTTPException(404, "Image not found")
    db.delete(img)
    db.commit()


@router.post("/review-requests/send")
async def send_review_request(
    payload: ReviewRequestIn,
    request: Request,
    org:     Organisation = Depends(require_role("owner", "admin")),
    user                  = Depends(get_current_user),
    db:      Session      = Depends(get_db),
):
    email = payload.email.lower().strip()

    existing_token = db.execute(
        select(ReviewToken).where(ReviewToken.org_id == org.id, ReviewToken.email == email)
    ).scalars().first()
    if existing_token and existing_token.used_at:
        raise HTTPException(409, f"{email} has already submitted a review.")

    rr = db.execute(
        select(ReviewRequest).where(ReviewRequest.org_id == org.id, ReviewRequest.email == email)
    ).scalars().first()
    if not rr:
        rr = ReviewRequest(id=uuid.uuid4(), org_id=org.id, sent_by=user.id, email=email)
        db.add(rr)
    rr.sent_at = datetime.now(timezone.utc)

    raw        = _new_token()
    token_hash = _hash_token(raw)
    expires    = datetime.now(timezone.utc) + timedelta(hours=48)

    if existing_token:
        existing_token.token_hash = token_hash
        existing_token.expires_at = expires
        existing_token.used_at    = None
    else:
        db.add(ReviewToken(
            id=uuid.uuid4(), org_id=org.id, email=email,
            token_hash=token_hash, expires_at=expires,
        ))

    db.commit()

    link  = _review_link(org.slug, raw, _frontend_url(request))
    note  = f'<div style="background:#f0f9ff;border-left:3px solid #6366f1;border-radius:8px;padding:14px 18px;margin:0 0 20px;"><p style="margin:0;color:#374151;font-size:14px;font-style:italic;">"{payload.message.strip()}"</p></div>' if payload.message else ""
    intro = f"We'd love to hear about your experience with <strong>{org.name}</strong>. Your feedback helps others make informed decisions."

    await send_email(
        to=email,
        subject=f"{org.name} would love your feedback",
        html=_email_html(org.name, link, intro, note),
    )
    return {"ok": True, "message": f"Review request sent to {email}"}


@router.get("/review-requests")
def list_review_requests(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(ReviewRequest).where(ReviewRequest.org_id == org.id)
        .order_by(ReviewRequest.sent_at.desc())
    ).scalars().all()
    return [r.to_dict() for r in rows]