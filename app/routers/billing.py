import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.paychangu import (
    initialize_mobile_money_payment,
    verify_mobile_money_payment,
)

# Adjust these imports only if your project uses different names
from app.dependencies.org import get_current_org
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/billing", tags=["billing"])


PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free",
        "amount": Decimal("0"),
        "limit_drafts": 20,
        "limit_brands": 1,
        "limit_members": 99,
    },
    "starter": {
        "name": "Starter",
        "amount": Decimal("15000"),
        "limit_drafts": 150,
        "limit_brands": 3,
        "limit_members": 99,
    },
    "pro": {
        "name": "Pro",
        "amount": Decimal("35000"),
        "limit_drafts": 500,
        "limit_brands": 10,
        "limit_members": 99,
    },
    "agency": {
        "name": "Agency",
        "amount": Decimal("90000"),
        "limit_drafts": None,
        "limit_brands": 999,
        "limit_members": 999,
    },
}


class InitializePayChanguIn(BaseModel):
    plan_id: str
    payment_method: str  # tnm | airtel
    mobile: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_mw_mobile(raw: str) -> str:
    """
    Accepts:
    - 0998970102
    - 998970102
    - +265998970102
    - 265998970102

    Returns local format used by PayChangu example:
    - 0998970102
    """
    digits = "".join(ch for ch in raw if ch.isdigit())

    if digits.startswith("265"):
        digits = "0" + digits[3:]


    if len(digits) != 10 or not digits.startswith("0"):
        raise HTTPException(status_code=400, detail="Invalid Malawi mobile number")

    if not (digits.startswith("08") or digits.startswith("09")):
        raise HTTPException(
            status_code=400,
            detail="Only Malawi mobile money numbers starting with 08 or 09 are supported",
        )

    return digits


def operator_ref_for_method(payment_method: str) -> str:
    method = payment_method.lower().strip()

    if method == "tnm":
        ref = os.getenv("PAYCHANGU_TNM_OPERATOR_REF_ID")
    elif method == "airtel":
        ref = os.getenv("PAYCHANGU_AIRTEL_OPERATOR_REF_ID")
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    if not ref:
        raise HTTPException(
            status_code=500,
            detail=f"PayChangu operator ref is not configured for {method}",
        )

    return ref


def extract_status(payload: dict) -> str:
    data = payload.get("data") or {}

    data_status = str(data.get("status") or "").lower().strip()
    root_status = str(payload.get("status") or "").lower().strip()

    # IMPORTANT:
    # initialize returns root status = success, but data.status = pending.
    # So data.status must win.
    if data_status in ("pending", "processing", "initiated"):
        return "pending"

    if data_status in ("success", "successful", "completed", "paid"):
        return "success"

    if data_status in ("failed", "failure", "cancelled", "canceled", "declined", "expired"):
        return "failed"

    # fallback for verify response
    if root_status in ("successful", "success"):
        return "success"

    if root_status in ("failed", "failure", "cancelled", "canceled", "declined", "expired"):
        return "failed"

    return "pending"


def activate_subscription(
    *,
    db: Session,
    org_id: str,
    payment_id: str,
    plan_id: str,
):
    plan = PLANS[plan_id]
    now = utcnow()
    period_end = now + timedelta(days=30)

    db.execute(
        text("""
            INSERT INTO billing_subscriptions
                (org_id, plan_id, status, current_period_start, current_period_end, last_payment_id, updated_at)
            VALUES
                (:org_id, :plan_id, 'active', :start_at, :end_at, :payment_id, now())
            ON CONFLICT (org_id)
            DO UPDATE SET
                plan_id = EXCLUDED.plan_id,
                status = 'active',
                current_period_start = EXCLUDED.current_period_start,
                current_period_end = EXCLUDED.current_period_end,
                last_payment_id = EXCLUDED.last_payment_id,
                updated_at = now()
        """),
        {
            "org_id": org_id,
            "plan_id": plan_id,
            "start_at": now,
            "end_at": period_end,
            "payment_id": payment_id,
        },
    )

    # Your schema already has organisation-level plan fields, so keep them synced.
    db.execute(
        text("""
            UPDATE organisations
            SET
                plan = :plan_id,
                plan_status = 'active',
                plan_started_at = :start_at,
                plan_expires_at = :end_at,
                monthly_draft_limit = :draft_limit,
                brand_limit = :brand_limit,
                member_limit = :member_limit,
                updated_at = now()
            WHERE id = :org_id
        """),
        {
            "org_id": org_id,
            "plan_id": plan_id,
            "start_at": now,
            "end_at": period_end,
            "draft_limit": plan["limit_drafts"],
            "brand_limit": plan["limit_brands"],
            "member_limit": plan["limit_members"],
        },
    )


@router.get("/plans")
def get_billing_plans():
    return {
        "plans": [
            {
                "id": key,
                "name": value["name"],
                "amount": float(value["amount"]),
                "currency": "MWK",
                "limit_drafts": value["limit_drafts"],
                "limit_brands": value["limit_brands"],
                "limit_members": value["limit_members"],
            }
            for key, value in PLANS.items()
        ]
    }


@router.get("/subscription")
def get_subscription(
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    row = db.execute(
        text("""
            SELECT
                bs.*,
                o.plan AS org_plan,
                o.plan_status,
                o.plan_expires_at
            FROM organisations o
            LEFT JOIN billing_subscriptions bs ON bs.org_id = o.id
            WHERE o.id = :org_id
            LIMIT 1
        """),
        {"org_id": str(org.id)},
    ).mappings().first()

    return {
        "subscription": dict(row) if row else None,
    }


@router.post("/paychangu/initialize")
async def initialize_paychangu_payment(
    payload: InitializePayChanguIn,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    plan_id = payload.plan_id.lower().strip()

    if plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    if plan_id == "free":
        raise HTTPException(status_code=400, detail="Free plan does not require payment")

    plan = PLANS[plan_id]
    mobile = normalize_mw_mobile(payload.mobile)
    method = payload.payment_method.lower().strip()
    operator_ref = operator_ref_for_method(method)

    charge_id = f"nf-{str(org.id)[:8]}-{plan_id}-{uuid.uuid4().hex[:12]}"

    db.execute(
        text("""
            INSERT INTO billing_payments
                (
                    org_id, user_id, plan_id, plan_name, amount, currency,
                    provider, payment_method, mobile, email, first_name, last_name,
                    charge_id, status, created_at, updated_at
                )
            VALUES
                (
                    :org_id, :user_id, :plan_id, :plan_name, :amount, 'MWK',
                    'paychangu', :payment_method, :mobile, :email, :first_name, :last_name,
                    :charge_id, 'pending', now(), now()
                )
        """),
        {
            "org_id": str(org.id),
            "user_id": str(user.id),
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "amount": plan["amount"],
            "payment_method": method,
            "mobile": mobile,
            "email": payload.email,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "charge_id": charge_id,
        },
    )
    db.commit()

    try:
        paychangu_response = await initialize_mobile_money_payment(
            mobile_money_operator_ref_id=operator_ref,
            amount=str(int(plan["amount"])),
            charge_id=charge_id,
            mobile=mobile,
            email=str(payload.email) if payload.email else None,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except Exception:
        db.execute(
            text("""
                UPDATE billing_payments
                SET status = 'failed', failure_reason = 'PayChangu initialization failed', updated_at = now()
                WHERE charge_id = :charge_id
            """),
            {"charge_id": charge_id},
        )
        db.commit()
        raise

    db.execute(
        text("""
            UPDATE billing_payments
            SET raw_initialize_response = CAST(:raw AS jsonb), updated_at = now()
            WHERE charge_id = :charge_id
        """),
        {
            "charge_id": charge_id,
            "raw": __import__("json").dumps(paychangu_response),
        },
    )
    db.commit()

    return {
        "ok": True,
        "message": "Payment request sent. Authorise it on your phone.",
        "charge_id": charge_id,
        "payment": {
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "amount": float(plan["amount"]),
            "currency": "MWK",
            "status": "pending",
            "mobile": mobile,
            "payment_method": method,
        },
        "paychangu": paychangu_response,
    }


@router.get("/payments/{charge_id}")
async def get_payment_status(
    charge_id: str,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    payment = db.execute(
        text("""
            SELECT *
            FROM billing_payments
            WHERE charge_id = :charge_id
              AND org_id = :org_id
            LIMIT 1
        """),
        {"charge_id": charge_id, "org_id": str(org.id)},
    ).mappings().first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    verify_response = await verify_mobile_money_payment(charge_id)
    normalized_status = extract_status(verify_response)

    db.execute(
        text("""
            UPDATE billing_payments
            SET
                status = :status,
                raw_verify_response = CAST(:raw AS jsonb),
                paid_at = CASE WHEN :status = 'success' AND paid_at IS NULL THEN now() ELSE paid_at END,
                updated_at = now()
            WHERE charge_id = :charge_id
        """),
        {
            "charge_id": charge_id,
            "status": normalized_status,
            "raw": __import__("json").dumps(verify_response),
        },
    )

    if normalized_status == "success":
        activate_subscription(
            db=db,
            org_id=str(org.id),
            payment_id=str(payment["id"]),
            plan_id=payment["plan_id"],
        )

    db.commit()

    return {
        "ok": True,
        "charge_id": charge_id,
        "status": normalized_status,
        "payment": dict(payment),
        "verify": verify_response,
    }


@router.post("/webhook/paychangu")
async def paychangu_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()

    data = payload.get("data") or {}
    charge_id = (
        data.get("charge_id")
        or data.get("chargeId")
        or payload.get("charge_id")
        or payload.get("chargeId")
    )

    if not charge_id:
        raise HTTPException(status_code=400, detail="Missing charge_id")

    payment = db.execute(
        text("""
            SELECT *
            FROM billing_payments
            WHERE charge_id = :charge_id
            LIMIT 1
        """),
        {"charge_id": charge_id},
    ).mappings().first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    verify_response = await verify_mobile_money_payment(charge_id)
    normalized_status = extract_status(verify_response)

    db.execute(
        text("""
            UPDATE billing_payments
            SET
                status = :status,
                raw_webhook_payload = CAST(:webhook AS jsonb),
                raw_verify_response = CAST(:verify AS jsonb),
                paid_at = CASE WHEN :status = 'success' AND paid_at IS NULL THEN now() ELSE paid_at END,
                updated_at = now()
            WHERE charge_id = :charge_id
        """),
        {
            "charge_id": charge_id,
            "status": normalized_status,
            "webhook": __import__("json").dumps(payload),
            "verify": __import__("json").dumps(verify_response),
        },
    )

    if normalized_status == "success":
        activate_subscription(
            db=db,
            org_id=str(payment["org_id"]),
            payment_id=str(payment["id"]),
            plan_id=payment["plan_id"],
        )

    db.commit()

    return {"ok": True}