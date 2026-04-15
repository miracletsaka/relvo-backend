from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.platform import PlatformCreate, PlatformUpdate, PlatformOut
from app.dependencies.org import get_current_org
from app.models.organisation import Organisation

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformOut])
def list_platforms(
    active_only: bool = Query(True),
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    sql = """
        SELECT id, display_name, is_active, org_id
        FROM platforms
        WHERE org_id = :org_id
    """
    params = {"org_id": str(org.id)}

    if active_only:
        sql += " AND is_active = true"

    sql += " ORDER BY display_name ASC"

    rows = db.execute(text(sql), params).mappings().all()

    return [
        {
            "id": r["id"],
            "display_name": r["display_name"],
            "is_active": r["is_active"],
            "org_id": str(r["org_id"]) if r["org_id"] else None,
        }
        for r in rows
    ]


@router.post("", response_model=PlatformOut, status_code=201)
def create_platform(
    payload: PlatformCreate,
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    platform_id = payload.id.strip().lower()

    existing = db.execute(text("""
        SELECT id
        FROM platforms
        WHERE id = :id AND org_id = :org_id
        LIMIT 1
    """), {
        "id": platform_id,
        "org_id": str(org.id),
    }).mappings().first()

    if existing:
        raise HTTPException(status_code=400, detail="Platform id already exists")

    db.execute(text("""
        INSERT INTO platforms
            (id, display_name, is_active, org_id)
        VALUES
            (:id, :display_name, :is_active, :org_id)
    """), {
        "id": platform_id,
        "display_name": payload.display_name.strip(),
        "is_active": payload.is_active,
        "org_id": str(org.id),
    })
    db.commit()

    row = db.execute(text("""
        SELECT id, display_name, is_active, org_id
        FROM platforms
        WHERE id = :id AND org_id = :org_id
        LIMIT 1
    """), {
        "id": platform_id,
        "org_id": str(org.id),
    }).mappings().first()

    if not row:
        raise HTTPException(status_code=500, detail="Platform created but could not be reloaded")

    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "is_active": row["is_active"],
        "org_id": str(row["org_id"]) if row["org_id"] else None,
    }


@router.patch("/{platform_id}", response_model=PlatformOut)
def update_platform(
    platform_id: str,
    payload: PlatformUpdate,
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    row = db.execute(text("""
        SELECT id, display_name, is_active, org_id
        FROM platforms
        WHERE id = :id AND org_id = :org_id
        LIMIT 1
    """), {
        "id": platform_id,
        "org_id": str(org.id),
    }).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Platform not found")

    new_display_name = payload.display_name.strip() if payload.display_name is not None else row["display_name"]
    new_is_active = payload.is_active if payload.is_active is not None else row["is_active"]

    db.execute(text("""
        UPDATE platforms
        SET display_name = :display_name,
            is_active = :is_active
        WHERE id = :id AND org_id = :org_id
    """), {
        "id": platform_id,
        "org_id": str(org.id),
        "display_name": new_display_name,
        "is_active": new_is_active,
    })
    db.commit()

    updated = db.execute(text("""
        SELECT id, display_name, is_active, org_id
        FROM platforms
        WHERE id = :id AND org_id = :org_id
        LIMIT 1
    """), {
        "id": platform_id,
        "org_id": str(org.id),
    }).mappings().first()

    return {
        "id": updated["id"],
        "display_name": updated["display_name"],
        "is_active": updated["is_active"],
        "org_id": str(updated["org_id"]) if updated["org_id"] else None,
    }