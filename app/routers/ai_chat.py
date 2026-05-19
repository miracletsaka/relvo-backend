import json
import os
from datetime import datetime, timezone
from uuid import UUID
from app.ai.app_links import APP_LINKS_CONTEXT
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import desc, text
from sqlalchemy.orm import Session
from app.services.google_connection import get_drive_service, get_docs_service
from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.ai_chat import AiChatMessage, AiChatThread

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_MEMORY_MESSAGES = 14


class CreateThreadRequest(BaseModel):
    title: str | None = None
    brand_id: str | None = None
    tone_id: str | None = None


class CreateMessageRequest(BaseModel):
    role: str = "user"
    content: str
    message_type: str = "text"
    metadata: dict | None = None


class ReplyRequest(BaseModel):
    content: str
    brand_id: str | None = None
    tone_id: str | None = None


class UpdateMessageRequest(BaseModel):
    content: str | None = None
    message_type: str | None = None
    metadata: dict | None = None
    draft_id: str | None = None
    canvas_state_id: str | None = None


class UpdateThreadRequest(BaseModel):
    title: str | None = None
    brand_id: str | None = None
    tone_id: str | None = None
    status: str | None = None

def search_google_docs_for_ai(db: Session, org_id, query: str, limit: int = 5):
    drive = get_drive_service(db=db, org_id=org_id)

    def normalize(value: str) -> str:
        return (
            str(value or "")
            .lower()
            .replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("-", " ")
            .replace("_", " ")
        )

    query_clean = " ".join(normalize(query).split())

    def list_docs(q_extra: str | None = None, page_size: int = 20):
        q_parts = [
            "mimeType='application/vnd.google-apps.document'",
            "trashed=false",
        ]

        if q_extra:
            q_parts.append(q_extra)

        res = (
            drive.files()
            .list(
                q=" and ".join(q_parts),
                pageSize=page_size,
                fields="files(id,name,mimeType,webViewLink,modifiedTime)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        return res.get("files", [])

    # 1. Direct Drive search using shorter keywords.
    if query_clean:
        words = [w for w in query_clean.split() if len(w) >= 4]

        for phrase in [
            query_clean,
            " ".join(words[:6]),
            " ".join(words[:4]),
            words[0] if words else "",
        ]:
            phrase = phrase.strip()

            if not phrase:
                continue

            safe = phrase.replace("'", "\\'")

            files = list_docs(f"name contains '{safe}'", page_size=limit)

            if files:
                return files

    # 2. Fallback: list recent docs and fuzzy match locally.
    recent_files = list_docs(None, page_size=30)

    if not query_clean:
        return recent_files[:limit]

    scored = []

    query_words = set(query_clean.split())

    for file in recent_files:
        title = normalize(file.get("name", ""))
        title_words = set(title.split())

        overlap = len(query_words.intersection(title_words))

        # Also catch direct substring either direction.
        substring_hit = query_clean in title or title in query_clean

        score = overlap + (10 if substring_hit else 0)

        if score > 0:
            scored.append((score, file))

    scored.sort(key=lambda item: item[0], reverse=True)

    if scored:
        return [file for _, file in scored[:limit]]

    return []


def extract_text_from_google_doc(document: dict) -> str:
    chunks = []

    def walk(elements):
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
                        walk(cell.get("content", []))

    walk(document.get("body", {}).get("content", []))

    return "\n".join([c for c in chunks if c.strip()])


def read_google_doc_for_ai(db: Session, org_id, file_id: str):
    docs = get_docs_service(db=db, org_id=org_id)
    document = docs.documents().get(documentId=file_id).execute()

    return {
        "title": document.get("title"),
        "text": extract_text_from_google_doc(document),
    }


def looks_like_doc_request(text: str) -> bool:
    t = text.lower()

    return any(
        phrase in t
        for phrase in [
            "google doc",
            "document",
            "doc",
            "summarize",
            "analyse",
            "analyze",
            "read my",
            "read the",
        ]
    )


def extract_doc_query(text: str) -> str:
    cleaned = text.lower()

    for phrase in [
        "summarize",
        "analyse",
        "analyze",
        "read my",
        "read the",
        "read",
        "google doc",
        "document",
        "doc",
    ]:
        cleaned = cleaned.replace(phrase, " ")

    return " ".join(cleaned.split()).strip()

def serialize_message(msg: AiChatMessage) -> dict:
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "message_type": msg.message_type,
        "metadata": msg.meta_json or {},
        "draft_id": str(msg.draft_id) if msg.draft_id else None,
        "canvas_state_id": str(msg.canvas_state_id) if msg.canvas_state_id else None,
        "created_at": msg.created_at,
    }


def should_generate_title(thread: AiChatThread) -> bool:
    return not thread.title or thread.title in ["New chat", "New marketing chat"]


def generate_chat_title(user_text: str) -> str:
    clean = " ".join((user_text or "").strip().split())

    if not clean:
        return "New conversation"

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a short ChatGPT-style title for this marketing assistant conversation. "
                        "Maximum 5 words. No quotes. No punctuation at the end. "
                        "If the message is only a greeting, return: General discussion."
                    ),
                },
                {"role": "user", "content": clean},
            ],
        )

        title = (res.choices[0].message.content or "").strip()
        title = title.replace('"', "").replace("'", "")
        return title[:60] or "New conversation"

    except Exception:
        if clean.lower() in {"hi", "hie", "hello", "hey"}:
            return "General discussion"

        return clean[:48] + ("..." if len(clean) > 48 else "")


def build_recent_conversation_context(
    db: Session,
    thread_id: UUID,
    org_id,
) -> str:
    rows = (
        db.query(AiChatMessage)
        .filter(
            AiChatMessage.thread_id == thread_id,
            AiChatMessage.org_id == org_id,
        )
        .order_by(desc(AiChatMessage.created_at))
        .limit(MAX_MEMORY_MESSAGES)
        .all()
    )

    rows.reverse()

    chunks: list[str] = []

    for row in rows:
        content = (row.content or "").strip()

        if not content:
            continue

        role = "User" if row.role == "user" else "Assistant"
        chunks.append(f"{role}: {content}")

    return "\n".join(chunks)


def build_org_context(org) -> str:
    fields = {
        "Organisation ID": getattr(org, "id", None),
        "Organisation name": getattr(org, "name", None),
        "Slug": getattr(org, "slug", None),
        "Description": getattr(org, "description", None),
        "Website": getattr(org, "website", None),
        "Business type": getattr(org, "business_type", None),
        "Tagline": getattr(org, "tagline", None),
        "Logo": getattr(org, "logo_url", None),
    }

    lines = []

    for key, value in fields.items():
        if value is not None and str(value).strip():
            lines.append(f"{key}: {value}")

    return "\n".join(lines) or "No organisation profile details available yet."


def build_ai_system_prompt(
    org_context: str,
    recent_context: str,
) -> str:
    return f"""
You are NeuroFlow AI, an elite AI business partner inside the user's business workspace.

You help the user with:
- marketing strategy
- automation systems
- campaign planning
- branding
- lead conversion
- AI implementation
- social content
- business growth ideas
- product and service positioning

You must act like a strategic business partner, not a generic chatbot.

APP LINKS:
{APP_LINKS_CONTEXT}

ORGANISATION CONTEXT:
{org_context}

RECENT CONVERSATION MEMORY:
{recent_context or "No recent conversation yet."}

- When mentioning an app feature, always include the markdown link from APP LINKS.
- Use markdown links exactly like: [Google Docs integration](/dashboard/integrations/google)
- Do not say "go to integrations" without providing the clickable app link.

Rules:
- Remember and use the recent conversation.
- Use the organisation context when relevant.
- Be practical, direct, and business-focused.
- Give clear next steps.
- Do not sound robotic.
- If the user wants an image, campaign post, advert, poster, or creative, respond briefly and let the system generate it.
- If the user asks for a monthly content plan, respond briefly and let the system generate it.
- Keep normal answers concise but useful.
""".strip()


def generate_normal_chat_reply(
    user_text: str,
    org_context: str,
    recent_context: str,
) -> str:
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": build_ai_system_prompt(
                        org_context=org_context,
                        recent_context=recent_context,
                    ),
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ],
        )

        return (res.choices[0].message.content or "I understand.").strip()

    except Exception:
        return "I understand. Tell me more and I’ll help you shape it into a clear business action."


def detect_chat_intent(user_text: str) -> dict:
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": """
You are an intent router for a brand-aware AI marketing chatbot.

Return STRICT JSON only. No markdown. No explanations.

Allowed intents:
- normal_chat
- generate_image
- generate_month_content
- analyze_business

Rules:
Use generate_image when the user asks to create/generate/design one ad, poster, image, creative, campaign post, social post, or advert.

Use generate_month_content when the user asks for a full month, content calendar, weekly plan, many posts, or scheduled content.

Use analyze_business when the user asks to analyze, audit, review, evaluate, compare, visualize, show insights, show data, show charts, check performance, or understand business health/data.

Use normal_chat for questions, strategy, explanations, ideas, brand advice, or general conversation.

JSON shape:
{
  "intent": "normal_chat" | "generate_image" | "generate_month_content" | "analyze_business",
  "reply": "short helpful response",
  "generation_prompt": "clean prompt to use for generation or null",
  "needs_visualization": true,
  "visualization_type": "chart_and_table",
  "analysis_focus": "short focus or null"
}
""",
            },
            {"role": "user", "content": user_text},
        ],
    )

    raw = res.choices[0].message.content or "{}"

    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "intent": "normal_chat",
            "reply": "I understand. Tell me what you want to create next.",
            "generation_prompt": None,
            "needs_visualization": False,
            "visualization_type": None,
            "analysis_focus": None,
        }

    intent = data.get("intent") or "normal_chat"

    if intent not in [
        "normal_chat",
        "generate_image",
        "generate_month_content",
        "analyze_business",
    ]:
        intent = "normal_chat"

    return {
        "intent": intent,
        "reply": data.get("reply") or "I understand.",
        "generation_prompt": data.get("generation_prompt"),
        "needs_visualization": bool(data.get("needs_visualization")),
        "visualization_type": data.get("visualization_type"),
        "analysis_focus": data.get("analysis_focus"),
    }

def safe_count(db: Session, sql: str, params: dict) -> int:
    try:
        value = db.execute(text(sql), params).scalar()
        return int(value or 0)
    except Exception:
        return 0


def build_business_analysis_payload(db: Session, org) -> dict:
    org_id = str(getattr(org, "id", ""))

    reviews_count = safe_count(
        db,
        "SELECT COUNT(*) FROM org_reviews WHERE org_id = :org_id",
        {"org_id": org_id},
    )

    offers_count = safe_count(
        db,
        "SELECT COUNT(*) FROM org_offers WHERE org_id = :org_id AND is_active = true",
        {"org_id": org_id},
    )

    media_count = safe_count(
        db,
        "SELECT COUNT(*) FROM media_assets WHERE org_id = :org_id",
        {"org_id": org_id},
    )

    google_connected = safe_count(
        db,
        "SELECT COUNT(*) FROM google_connections WHERE org_id = :org_id",
        {"org_id": org_id},
    ) > 0

    profile_fields = [
        getattr(org, "name", None),
        getattr(org, "description", None),
        getattr(org, "website", None),
        getattr(org, "business_type", None),
        getattr(org, "tagline", None),
        getattr(org, "logo_url", None),
    ]

    profile_score = round(
        (len([v for v in profile_fields if v and str(v).strip()]) / len(profile_fields)) * 100
    )

    reviews_score = min(100, reviews_count * 20)
    offers_score = min(100, offers_count * 35)
    media_score = min(100, media_count * 12)
    docs_score = 100 if google_connected else 0

    overall_score = round(
        (profile_score + reviews_score + offers_score + media_score + docs_score) / 5
    )

    return {
        "type": "business_analysis",
        "summary": {
            "business_name": getattr(org, "name", None),
            "overall_score": overall_score,
            "google_docs_connected": google_connected,
        },
        "charts": [
            {
                "type": "bar",
                "title": "Business AI readiness",
                "data": [
                    {"label": "Profile", "value": profile_score},
                    {"label": "Reviews", "value": reviews_score},
                    {"label": "Offers", "value": offers_score},
                    {"label": "Media", "value": media_score},
                    {"label": "Docs", "value": docs_score},
                ],
            }
        ],
        "table": {
            "title": "Recommended improvements",
            "columns": ["Area", "Score", "Recommendation"],
            "rows": [
                ["Profile", f"{profile_score}%", "Complete business description, website, logo, and positioning."],
                ["Reviews", f"{reviews_score}%", "Collect more customer reviews for social proof and stronger campaigns."],
                ["Offers", f"{offers_score}%", "Add clear offers with CTA text to improve conversion-focused content."],
                ["Media", f"{media_score}%", "Upload more product, service, team, or brand images."],
                ["Google Docs", f"{docs_score}%", "Connect Google Docs so AI can understand proposals, notes, SOPs, and plans."],
            ],
        },
    }


def generate_business_analysis_reply(
    user_text: str,
    org_context: str,
    recent_context: str,
    analysis_payload: dict,
) -> str:
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.35,
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are Relvo's business analysis assistant inside the user's workspace.

Use the organisation context, recent conversation, and analysis payload.
Explain the business health clearly.
Mention that a chart/table is being shown in the chat UI.
Give practical recommendations.
Be concise, accurate, and strategic.

APP LINKS:
{APP_LINKS_CONTEXT}
""",
                },
                {
                    "role": "user",
                    "content": f"""
User request:
{user_text}

Organisation context:
{org_context}

Recent conversation:
{recent_context}

Analysis payload:
{json.dumps(analysis_payload, indent=2)}
""",
                },
            ],
        )

        return (res.choices[0].message.content or "").strip() or "Here is the business analysis."
    except Exception:
        return "Here is a quick business analysis. I reviewed the profile, reviews, offers, media assets, and connected documents to estimate how ready this business is for better AI-generated campaigns."

@router.patch("/threads/{thread_id}")
def update_thread(
    thread_id: UUID,
    payload: UpdateThreadRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    thread = (
        db.query(AiChatThread)
        .filter(AiChatThread.id == thread_id, AiChatThread.org_id == org.id)
        .first()
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if payload.title is not None:
        thread.title = payload.title

    if payload.brand_id is not None:
        thread.brand_id = payload.brand_id

    if payload.tone_id is not None:
        thread.tone_id = payload.tone_id

    if payload.status is not None:
        thread.status = payload.status

    thread.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(thread)

    return {
        "id": str(thread.id),
        "title": thread.title,
        "status": thread.status,
        "brand_id": thread.brand_id,
        "tone_id": str(thread.tone_id) if thread.tone_id else None,
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
    }


@router.patch("/messages/{message_id}")
def update_message(
    message_id: UUID,
    payload: UpdateMessageRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    msg = (
        db.query(AiChatMessage)
        .filter(
            AiChatMessage.id == message_id,
            AiChatMessage.org_id == org.id,
        )
        .first()
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if payload.content is not None:
        msg.content = payload.content

    if payload.message_type is not None:
        msg.message_type = payload.message_type

    if payload.metadata is not None:
        msg.meta_json = payload.metadata

    if payload.draft_id:
        msg.draft_id = payload.draft_id

    if payload.canvas_state_id:
        msg.canvas_state_id = payload.canvas_state_id

    db.commit()
    db.refresh(msg)

    return serialize_message(msg)


@router.post("/threads")
def create_thread(
    payload: CreateThreadRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    thread = AiChatThread(
        org_id=org.id,
        brand_id=payload.brand_id,
        tone_id=payload.tone_id,
        title=payload.title or "New chat",
    )

    db.add(thread)
    db.commit()
    db.refresh(thread)

    return {
        "id": str(thread.id),
        "title": thread.title,
        "status": thread.status,
        "brand_id": thread.brand_id,
        "tone_id": str(thread.tone_id) if thread.tone_id else None,
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
    }


@router.get("/threads")
def list_threads(
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    rows = (
        db.query(AiChatThread)
        .filter(AiChatThread.org_id == org.id)
        .order_by(desc(AiChatThread.updated_at))
        .all()
    )

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "status": r.status,
            "brand_id": r.brand_id,
            "tone_id": str(r.tone_id) if r.tone_id else None,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.get("/threads/{thread_id}/messages")
def list_messages(
    thread_id: UUID,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    thread = (
        db.query(AiChatThread)
        .filter(AiChatThread.id == thread_id, AiChatThread.org_id == org.id)
        .first()
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    rows = (
        db.query(AiChatMessage)
        .filter(AiChatMessage.thread_id == thread_id, AiChatMessage.org_id == org.id)
        .order_by(AiChatMessage.created_at.asc())
        .all()
    )

    return [serialize_message(r) for r in rows]


@router.post("/threads/{thread_id}/messages")
def create_message(
    thread_id: UUID,
    payload: CreateMessageRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    thread = (
        db.query(AiChatThread)
        .filter(AiChatThread.id == thread_id, AiChatThread.org_id == org.id)
        .first()
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    msg = AiChatMessage(
        thread_id=thread.id,
        org_id=org.id,
        role=payload.role,
        content=payload.content,
        message_type=payload.message_type,
        meta_json=payload.metadata or {},
    )

    thread.updated_at = datetime.now(timezone.utc)

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return serialize_message(msg)


@router.post("/threads/{thread_id}/reply")
def reply_to_thread(
    thread_id: UUID,
    payload: ReplyRequest,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    thread = (
        db.query(AiChatThread)
        .filter(AiChatThread.id == thread_id, AiChatThread.org_id == org.id)
        .first()
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_text = (payload.content or "").strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message is required")

    recent_context = build_recent_conversation_context(
        db=db,
        thread_id=thread.id,
        org_id=org.id,
    )

    org_context = build_org_context(org)

    intent_result = detect_chat_intent(user_text)

    doc_context = ""
    doc_meta = None
    analysis_payload = None

    if looks_like_doc_request(user_text):
        try:
            print("[AI CHAT] Google Docs request detected")

            doc_query = extract_doc_query(user_text)

            print("[AI CHAT] doc_query:", doc_query)

            files = search_google_docs_for_ai(
                db=db,
                org_id=org.id,
                query=doc_query,
                limit=3,
            )

            print("[AI CHAT] matched_files:", files)

            if files:
                selected_file = files[0]

                doc = read_google_doc_for_ai(
                    db=db,
                    org_id=org.id,
                    file_id=selected_file["id"],
                )

                doc_text = (doc.get("text") or "")[:12000]

                doc_context = f"""
GOOGLE DOCUMENT CONTEXT

Document title:
{doc.get("title")}

Document link:
{selected_file.get("webViewLink")}

Document content:
{doc_text}
"""

                doc_meta = {
                    "file_id": selected_file.get("id"),
                    "title": doc.get("title"),
                    "webViewLink": selected_file.get("webViewLink"),
                    "matched_files": files,
                }

                print("[AI CHAT] loaded_google_doc:", doc.get("title"))
            else:
                doc_context = """
GOOGLE DOCUMENT CONTEXT

No matching Google Doc was found for this request.
Tell the user no matching document was found and suggest trying the exact document title.
"""

        except Exception as e:
            print("[AI CHAT] Google Docs error:", e)

            doc_context = f"""
GOOGLE DOCUMENT CONTEXT

Google Docs access failed:
{str(e)}

Tell the user Google Docs appears connected incorrectly or needs reconnecting.
"""

            doc_meta = {
                "error": str(e),
            }

    if intent_result["intent"] == "analyze_business":
        analysis_payload = build_business_analysis_payload(
            db=db,
            org=org,
        )

        assistant_reply = generate_business_analysis_reply(
            user_text=user_text,
            org_context=org_context + "\n\n" + doc_context,
            recent_context=recent_context,
            analysis_payload=analysis_payload,
        )

    elif intent_result["intent"] == "normal_chat":
        assistant_reply = generate_normal_chat_reply(
            user_text=user_text,
            org_context=org_context + "\n\n" + doc_context,
            recent_context=recent_context,
        )

    else:
        assistant_reply = intent_result["reply"]

    user_msg = AiChatMessage(
        thread_id=thread.id,
        org_id=org.id,
        role="user",
        content=user_text,
        message_type="text",
        meta_json={},
    )


    # meta_json
    # intent

    assistant_msg = AiChatMessage(
        thread_id=thread.id,
        org_id=org.id,
        role="assistant",
        content=assistant_reply,
        message_type=intent_result["intent"],
        meta_json={
            "intent": intent_result["intent"],
            "generation_prompt": intent_result.get("generation_prompt"),
            "brand_id": payload.brand_id,
            "business_analysis": analysis_payload,
            "tone_id": payload.tone_id,
            "memory_used": True,
            "google_doc": doc_meta,
        },
    )

    if should_generate_title(thread):
        thread.title = generate_chat_title(user_text)

    thread.brand_id = payload.brand_id or thread.brand_id
    thread.tone_id = payload.tone_id or thread.tone_id
    thread.updated_at = datetime.now(timezone.utc)

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return {
        "user_message": serialize_message(user_msg),
        "assistant_message": serialize_message(assistant_msg),
        "intent": {
            **intent_result,
            "reply": assistant_reply,
            "business_analysis": analysis_payload,
            "google_doc": doc_meta,
        },
    }

