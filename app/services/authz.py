from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DbSession
from app.services.sessions import COOKIE_NAME, clear_session_cookie, hash_session_token
from app.database import get_db
from app.models.session import Session
from app.models.session import Session as UserSession
from app.models.user import User
from app.services.sessions import COOKIE_NAME, hash_session_token
from app.services.tokens import utcnow


def _get_current_session(
    req: Request,
    resp: Response,
    db: DbSession,
) -> UserSession:
    raw = req.cookies.get(COOKIE_NAME)

    if not raw:
        clear_session_cookie(resp)
        raise HTTPException(status_code=401, detail="Not authenticated")

    sh = hash_session_token(raw)

    sess = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == sh,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )

    if not sess or sess.expires_at < utcnow():
        clear_session_cookie(resp)

        if sess and sess.revoked_at is None:
            sess.revoked_at = utcnow()
            db.commit()

        raise HTTPException(status_code=401, detail="Session expired")

    return sess

def get_current_user(
    req: Request,
    resp: Response,
    db: DbSession = Depends(get_db),
) -> User:
    sess = _get_current_session(req, resp, db)

    user = db.query(User).filter(User.id == sess.user_id).first()

    if not user or not user.is_active:
        clear_session_cookie(resp)

        if sess and sess.revoked_at is None:
            sess.revoked_at = utcnow()
            db.commit()

        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_admin(
    user: User = Depends(get_current_user),  # ← chain instead of calling manually
) -> User:
    if getattr(user, "role", "member") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user