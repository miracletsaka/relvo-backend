"""
app/dependencies/org.py
───────────────────────
FastAPI dependencies that scope every request to an organisation.

Usage in any router:
    from app.dependencies.org import get_current_org, require_role

    @router.get("/brands")
    def list_brands(
        org: Organisation = Depends(get_current_org),
        db:  Session      = Depends(get_db),
    ):
        return db.execute(select(Brand).where(Brand.org_id == org.id)).scalars().all()
"""
from __future__ import annotations

from functools import wraps
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.organisation import Organisation, OrganisationMember, PLAN_LIMITS, UsageLog
from app.services.authz import get_current_user   # your existing auth dep
from datetime import datetime, timezone


# ── Core dependency ────────────────────────────────────────────────────────────

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organisation import Organisation, OrganisationMember, PLAN_LIMITS, UsageLog
from app.services.authz import get_current_user   # your existing auth dep


def get_current_org(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Resolves the current org from:
    1. user.current_org_id
    2. nf_org cookie
    3. X-Org-Id header

    Raises:
    - 401 if not logged in
    - 403 if no org selected
    - 404 if org not found
    """
    org_id: Optional[str] = None

    # user may be an object or a dict, so handle both safely
    if user is not None:
        if isinstance(user, dict):
            org_id = user.get("current_org_id")
            user_id = user.get("id")
        else:
            org_id = getattr(user, "current_org_id", None)
            user_id = getattr(user, "id", None)
    else:
        user_id = None

    # fallback to cookie
    if not org_id:
        org_id = request.cookies.get("nf_org")

    # fallback to header
    if not org_id:
        org_id = request.headers.get("X-Org-Id")

    if not org_id:
        raise HTTPException(
            status_code=403,
            detail="No organisation selected. Complete onboarding first."
        )

    try:
        oid = UUID(str(org_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid org_id")

    org = db.execute(
        select(Organisation).where(
            Organisation.id == oid,
            Organisation.is_active == True,
        )
    ).scalars().first()

    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id == oid,
            OrganisationMember.user_id == UUID(str(user_id)),
        )
    ).scalars().first()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organisation"
        )

    org._current_role = member.role
    return org


def get_current_org(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Resolves the current org from:
    1. user.current_org_id
    2. nf_org cookie
    3. X-Org-Id header
    """
    org_id: Optional[str] = None
    user_id: Optional[str] = None

    if user is not None:
        if isinstance(user, dict):
            org_id = user.get("current_org_id")
            user_id = user.get("id")
        else:
            org_id = getattr(user, "current_org_id", None)
            user_id = getattr(user, "id", None)

    if not org_id:
        org_id = request.cookies.get("nf_org")

    if not org_id:
        org_id = request.headers.get("X-Org-Id")

    if not org_id:
        raise HTTPException(
            status_code=403,
            detail="No organisation selected. Complete onboarding first."
        )

    try:
        oid = UUID(str(org_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid org_id")

    org = db.execute(
        select(Organisation).where(
            Organisation.id == oid,
            Organisation.is_active == True,
        )
    ).scalars().first()

    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.org_id == oid,
            OrganisationMember.user_id == UUID(str(user_id)),
        )
    ).scalars().first()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organisation"
        )

    org._current_role = member.role
    return org


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access.

    Example:
        org: Organisation = Depends(require_role("owner", "admin"))
    """
    def dependency(org: Organisation = Depends(get_current_org)):
        role = getattr(org, "_current_role", "member")

        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {' or '.join(allowed_roles)}. Your role: {role}"
            )

        return org

    return dependency

# ── Plan limit enforcement ─────────────────────────────────────────────────────

def check_limit(org: Organisation, db: Session, resource: str, current_count: int):
    """
    Raises 402 if the org has hit its plan limit for a resource.

    Usage:
        brand_count = db.execute(select(func.count()).where(Brand.org_id == org.id)).scalar()
        check_limit(org, db, "max_brands", brand_count)
    """
    limit = org.get_limit(resource)
    if current_count >= limit:
        plan = org.plan
        raise HTTPException(
            status_code=402,
            detail={
                "code":     "PLAN_LIMIT_REACHED",
                "resource": resource,
                "limit":    limit,
                "current":  current_count,
                "plan":     plan,
                "message":  f"You've reached the {resource.replace('_', ' ')} limit on the {plan} plan. Upgrade to continue.",
                "upgrade_url": "/billing/upgrade",
            }
        )


def track_usage(
    db:      Session,
    org_id:  UUID,
    user_id: Optional[UUID],
    action:  str,
    quantity: int = 1,
):
    """
    Log a usage event. Call after successfully creating a resource.

    Usage:
        track_usage(db, org.id, user.id, "draft_generated", quantity=len(drafts))
    """
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    db.add(UsageLog(
        org_id=org_id, user_id=user_id,
        action=action, quantity=quantity, period=period,
    ))
    # Don't commit here — caller commits with their own transaction


def get_monthly_usage(db: Session, org_id: UUID, action: str) -> int:
    """Return total usage for current month."""
    from sqlalchemy import func
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    result = db.execute(
        select(func.sum(UsageLog.quantity)).where(
            UsageLog.org_id  == org_id,
            UsageLog.action  == action,
            UsageLog.period  == period,
        )
    ).scalar()
    return result or 0