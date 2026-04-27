import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException


PAYCHANGU_BASE_URL = os.getenv("PAYCHANGU_BASE_URL", "https://api.paychangu.com").rstrip("/")
PAYCHANGU_SECRET_KEY = os.getenv("PAYCHANGU_SECRET_KEY")


def _headers() -> Dict[str, str]:
    if not PAYCHANGU_SECRET_KEY:
        raise HTTPException(status_code=500, detail="PAYCHANGU_SECRET_KEY is not configured")

    return {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {PAYCHANGU_SECRET_KEY}",
    }


async def initialize_mobile_money_payment(
    *,
    mobile_money_operator_ref_id: str,
    amount: str,
    charge_id: str,
    mobile: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{PAYCHANGU_BASE_URL}/mobile-money/payments/initialize"

    payload: Dict[str, Any] = {
        "mobile_money_operator_ref_id": mobile_money_operator_ref_id,
        "amount": amount,
        "charge_id": charge_id,
        "mobile": mobile,
    }

    if email:
        payload["email"] = email
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

        print(f"Initializing PayChangu payment with payload: {payload}")  # Debug log

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=_headers(), json=payload)
            data = res.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"PayChangu connection failed: {str(exc)}")
    except Exception:
        raise HTTPException(status_code=502, detail="PayChangu returned an invalid response")

    if res.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "PayChangu payment initialization failed",
                "paychangu_response": data,
            },
        )

    return data


async def verify_mobile_money_payment(charge_id: str) -> Dict[str, Any]:
    url = f"{PAYCHANGU_BASE_URL}/mobile-money/payments/{charge_id}/verify"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(url, headers=_headers())
            data = res.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"PayChangu verification failed: {str(exc)}")
    except Exception:
        raise HTTPException(status_code=502, detail="PayChangu returned an invalid verification response")

    if res.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "PayChangu payment verification failed",
                "paychangu_response": data,
            },
        )

    return data