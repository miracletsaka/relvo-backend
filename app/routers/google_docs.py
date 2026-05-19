"""
backend/app/routers/google_docs.py
─────────────────────────────────
Read/search Google Drive Docs connected to the current org.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.org import get_current_org
from app.services.google_connection import get_docs_service, get_drive_service
import json
from datetime import datetime, timezone
from openai import OpenAI
from sqlalchemy import text
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/google-docs", tags=["Google Docs"])


class ReadDocRequest(BaseModel):
    file_id: str

def summarize_doc_with_ai(title: str, doc_text: str) -> dict:
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.25,
        messages=[
            {
                "role": "system",
                "content": """
Return STRICT JSON only.

Summarise this business document for an AI business workspace.

JSON shape:
{
  "summary": "clear useful summary",
  "key_points": ["point 1", "point 2"],
  "action_items": ["action 1", "action 2"]
}
""",
            },
            {
                "role": "user",
                "content": f"""
Document title:
{title}

Document text:
{doc_text[:20000]}
""",
            },
        ],
    )

    raw = res.choices[0].message.content or "{}"

    try:
        return json.loads(raw)
    except Exception:
        return {
            "summary": raw,
            "key_points": [],
            "action_items": [],
        }
    
@router.post("/files/{file_id}/summarize")
def summarize_google_doc(
    file_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    existing = db.execute(
        text("""
            SELECT *
            FROM google_doc_summaries
            WHERE org_id = :org_id AND google_file_id = :file_id
            LIMIT 1
        """),
        {
            "org_id": str(org.id),
            "file_id": file_id,
        },
    ).mappings().first()

    if existing and not force:
        return {
            "cached": True,
            "summary": dict(existing),
        }

    drive = get_drive_service(db=db, org_id=org.id)
    file_meta = (
        drive.files()
        .get(fileId=file_id, fields="id,name,webViewLink,modifiedTime")
        .execute()
    )

    doc = read_google_doc(
        file_id=file_id,
        db=db,
        org=org,
        user=user,
    )

    ai_summary = summarize_doc_with_ai(
        title=doc.get("title") or file_meta.get("name") or "Untitled",
        doc_text=doc.get("text") or "",
    )

    db.execute(
        text("""
            INSERT INTO google_doc_summaries
                (org_id, google_file_id, title, web_view_link, summary,
                 key_points, action_items, source_modified_time, summarized_at, updated_at)
            VALUES
                (:org_id, :google_file_id, :title, :web_view_link, :summary,
                 CAST(:key_points AS jsonb), CAST(:action_items AS jsonb),
                 :source_modified_time, now(), now())
            ON CONFLICT (org_id, google_file_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                web_view_link = EXCLUDED.web_view_link,
                summary = EXCLUDED.summary,
                key_points = EXCLUDED.key_points,
                action_items = EXCLUDED.action_items,
                source_modified_time = EXCLUDED.source_modified_time,
                summarized_at = now(),
                updated_at = now()
        """),
        {
            "org_id": str(org.id),
            "google_file_id": file_id,
            "title": doc.get("title") or file_meta.get("name"),
            "web_view_link": file_meta.get("webViewLink"),
            "summary": ai_summary.get("summary") or "",
            "key_points": json.dumps(ai_summary.get("key_points") or []),
            "action_items": json.dumps(ai_summary.get("action_items") or []),
            "source_modified_time": file_meta.get("modifiedTime"),
        },
    )

    db.commit()

    saved = db.execute(
        text("""
            SELECT *
            FROM google_doc_summaries
            WHERE org_id = :org_id AND google_file_id = :file_id
            LIMIT 1
        """),
        {
            "org_id": str(org.id),
            "file_id": file_id,
        },
    ).mappings().first()

    return {
        "cached": False,
        "summary": dict(saved),
    }

def _extract_text_from_doc(document: dict) -> str:
    chunks: list[str] = []

    def walk_elements(elements):
        for element in elements or []:
            paragraph = element.get("paragraph")
            if paragraph:
                line = []
                for pe in paragraph.get("elements", []):
                    text_run = pe.get("textRun")
                    if text_run and text_run.get("content"):
                        line.append(text_run["content"])
                if line:
                    chunks.append("".join(line).rstrip())

            table = element.get("table")
            if table:
                for row in table.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk_elements(cell.get("content", []))

    body = document.get("body", {})
    walk_elements(body.get("content", []))

    return "\n".join([chunk for chunk in chunks if chunk.strip()])


@router.get("/files")
def list_google_docs(
    q: str | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    drive = get_drive_service(db=db, org_id=org.id)

    query_parts = [
        "mimeType='application/vnd.google-apps.document'",
        "trashed=false",
    ]

    if q and q.strip():
        safe = q.strip().replace("'", "\\'")
        query_parts.append(f"name contains '{safe}'")

    res = (
        drive.files()
        .list(
            q=" and ".join(query_parts),
            pageSize=page_size,
            fields="files(id,name,mimeType,webViewLink,modifiedTime,owners(displayName,emailAddress))",
            orderBy="modifiedTime desc",
        )
        .execute()
    )

    return {"files": res.get("files", [])}


@router.get("/files/{file_id}")
def read_google_doc(
    file_id: str,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    docs = get_docs_service(db=db, org_id=org.id)

    try:
        document = docs.documents().get(documentId=file_id).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Google Doc: {e}")

    return {
        "file_id": file_id,
        "title": document.get("title"),
        "text": _extract_text_from_doc(document),
        "raw": document,
    }


@router.post("/read")
def read_google_doc_post(
    payload: ReadDocRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
    user=Depends(get_current_user),
):
    return read_google_doc(file_id=payload.file_id, db=db, org=org, user=user)
