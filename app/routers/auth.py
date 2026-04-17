from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session as DbSession
from datetime import timedelta, datetime, timezone
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.session import Session as UserSession
from app.models.email_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.organisation import Organisation, OrganisationMember
from app.services.passwords import hash_password, verify_password, generate_temp_password
from app.services.tokens import new_token, hash_token, utcnow, expires_in
from app.services.mailer import send_email, verify_link, reset_link
from app.services.sessions import (
    new_session_token,
    hash_session_token,
    set_session_cookie,
    clear_session_cookie,
    set_org_cookie,
    clear_org_cookie,
    COOKIE_NAME,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ResetRequestIn(BaseModel):
    email: EmailStr


class ResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


def _get_current_session(req: Request, db: DbSession) -> UserSession:
    raw = req.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sh = hash_session_token(raw)
    sess = (
        db.query(UserSession)
        .filter(UserSession.session_token == sh, UserSession.revoked_at.is_(None))
        .first()
    )

    if not sess or sess.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Session expired")

    return sess


def _get_current_user_from_session(req: Request, db: DbSession) -> tuple[UserSession, User]:
    sess = _get_current_session(req, db)

    user = db.query(User).filter(User.id == sess.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return sess, user


@router.post("/register")
async def register(payload: RegisterIn, db: DbSession = Depends(get_db)):
    email = payload.email.lower().strip()
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()

    if not first_name:
        raise HTTPException(status_code=400, detail="First name is required")

    if not last_name:
        raise HTTPException(status_code=400, detail="Last name is required")

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_password = generate_temp_password(12)

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password_hash=hash_password(temp_password),
        is_email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = new_token()
    t = EmailVerificationToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=expires_in(24 * 60),
        used_at=None,
    )
    db.add(t)
    db.commit()

    link = verify_link(token)

    await send_email(
        to=user.email,
        subject="Verify your email",
        html=f"""
        <div style="font-family: Arial, Helvetica, sans-serif; background:#f6f7fb; padding:32px;">
          <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; padding:32px;">
            <h2 style="margin:0 0 16px; color:#111827;">Welcome to Relvō AI</h2>
            <p style="margin:0 0 12px; color:#374151; font-size:14px; line-height:1.6;">
              Hi {first_name},
            </p>
            <p style="margin:0 0 16px; color:#374151; font-size:14px; line-height:1.6;">
              Please verify your email address by clicking the button below.
            </p>

            <div style="margin:24px 0;">
              <a href="{link}" style="display:inline-block; background:#6d28d9; color:#ffffff; text-decoration:none; padding:12px 18px; border-radius:10px; font-size:14px; font-weight:700;">
                Verify Email
              </a>
            </div>

            <p style="margin:0 0 10px; color:#374151; font-size:14px; line-height:1.6;">
              Your temporary password is:
            </p>
            <div style="margin:0 0 18px; padding:12px 14px; background:#f3f4f6; border-radius:10px; font-size:14px; color:#111827; font-weight:700;">
              {temp_password}
            </div>

            <p style="margin:0 0 8px; color:#6b7280; font-size:13px; line-height:1.6;">
              After verifying your email and signing in, please change your password in settings.
            </p>

            <p style="margin:18px 0 0; color:#9ca3af; font-size:12px; line-height:1.6;">
              If the button does not work, use this link:<br />
              <a href="{link}" style="color:#6d28d9;">{link}</a>
            </p>
          </div>
        </div>
        """,
    )

    return {"ok": True, "message": "Check your email to verify your account."}


@router.get("/verify-email")
def verify_email(token: str, db: DbSession = Depends(get_db)):
    def utcnow_aware() -> datetime:
        return datetime.now(timezone.utc)

    th = hash_token(token)

    row = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token == th)
        .first()
    )

    if not row or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or used token")

    expires_at = row.expires_at
    if expires_at is None:
        raise HTTPException(status_code=400, detail="Token expired")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < utcnow_aware():
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.is_email_verified = True
    row.used_at = utcnow_aware()

    db.commit()

    return {
        "ok": True,
        "message": "Email verified successfully. Redirecting to login...",
    }


@router.post("/login")
def login(payload: LoginIn, req: Request, resp: Response, db: DbSession = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    st = new_session_token()
    sess = UserSession(
        user_id=user.id,
        session_token=hash_session_token(st),
        expires_at=utcnow() + timedelta(days=7),
        revoked_at=None,
        user_agent=req.headers.get("user-agent"),
        ip_address=req.client.host if req.client else None,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    set_session_cookie(resp, st)

    # If user belongs to an org, set nf_org too
    membership = (
        db.query(OrganisationMember)
        .filter(OrganisationMember.user_id == user.id)
        # .order_by(OrganisationMember.created_at.asc())
        .first()
    )
    if membership:
        set_org_cookie(resp, str(membership.org_id))

    return {"ok": True}


@router.post("/logout")
def logout(req: Request, resp: Response, db: DbSession = Depends(get_db)):
    raw = req.cookies.get(COOKIE_NAME)
    if raw:
        sh = hash_session_token(raw)
        sess = (
            db.query(UserSession)
            .filter(UserSession.session_token == sh, UserSession.revoked_at.is_(None))
            .first()
        )
        if sess:
            sess.revoked_at = utcnow()
            db.commit()

    clear_session_cookie(resp)
    clear_org_cookie(resp)
    return {"ok": True}


@router.get("/me")
def get_me(request: Request, db: DbSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hash_session_token(token)

    session = db.execute(
        select(UserSession).where(
            UserSession.session_token == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    ).scalars().first()

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.execute(
        select(User).where(User.id == session.user_id)
    ).scalars().first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    org_id = str(session.org_id) if session.org_id else None
    role = None

    if org_id:
        member = db.execute(
            select(OrganisationMember).where(
                OrganisationMember.org_id == session.org_id,
                OrganisationMember.user_id == user.id,
            )
        ).scalars().first()
        role = member.role if member else "member"

    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "org_id": org_id,
        "role": role,
        "is_email_verified": user.is_email_verified,
    }


@router.post("/password-reset/request")
async def password_reset_request(payload: ResetRequestIn, db: DbSession = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return {"ok": True}

    token = new_token()
    row = PasswordResetToken(
        user_id=user.id,
        token=hash_token(token),
        expires_at=expires_in(45),
        used_at=None,
    )
    db.add(row)
    db.commit()

    link = reset_link(token)
    await send_email(
        to=user.email,
        subject="Reset your password",
        html=f"<p>Reset your password:</p><p><a href='{link}'>{link}</a></p>",
    )
    return {"ok": True}


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: ResetConfirmIn, db: DbSession = Depends(get_db)):
    th = hash_token(payload.token)
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token == th).first()
    if not row or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if row.expires_at < utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    row.used_at = utcnow()

    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None)
    ).update({"revoked_at": utcnow()})

    db.commit()
    return {"ok": True}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, req: Request, db: DbSession = Depends(get_db)):
    sess, user = _get_current_user_from_session(req, db)

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different")

    user.password_hash = hash_password(payload.new_password)

    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
        UserSession.session_token != sess.session_token,
    ).update({"revoked_at": utcnow()})

    db.commit()
    return {"ok": True}


@router.delete("/me", status_code=204)
def delete_my_account(req: Request, resp: Response, db: DbSession = Depends(get_db)):
    """
    Delete the currently authenticated user's own account.
    Also clears all sessions and cookies.
    """
    sess, user = _get_current_user_from_session(req, db)
    user_id = user.id

    # Revoke/delete sessions
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()

    # Delete tokens
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).delete()
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

    # Delete memberships
    db.query(OrganisationMember).filter(OrganisationMember.user_id == user_id).delete()

    # Delete user
    db.delete(user)
    db.commit()

    clear_session_cookie(resp)
    clear_org_cookie(resp)
    return Response(status_code=204)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, req: Request,resp: Response, db: DbSession = Depends(get_db)):
    """
    Admin-style delete of another user.
    Prevents self-deletion here; self-deletion is handled by DELETE /auth/me.
    """
    sess = _get_current_session(req, db)

    if str(sess.user_id) == str(user_id):
        sess, user = _get_current_user_from_session(req, db)
        user_id = user.id

        # Revoke/delete sessions
        db.query(UserSession).filter(UserSession.user_id == user_id).delete()

        # Delete tokens
        db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).delete()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

        # Delete memberships
        db.query(OrganisationMember).filter(OrganisationMember.user_id == user_id).delete()

        # Delete user
        db.delete(user)
        db.commit()

        raw = req.cookies.get(COOKIE_NAME)
        if raw:
            sh = hash_session_token(raw)
            sess = (
                db.query(UserSession)
                .filter(UserSession.session_token == sh, UserSession.revoked_at.is_(None))
                .first()
            )
            if sess:
                sess.revoked_at = utcnow()
                db.commit()

            clear_session_cookie(resp)
            clear_org_cookie(resp)
            return Response(status_code=204)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).delete()
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
    db.query(OrganisationMember).filter(OrganisationMember.user_id == user_id).delete()

    db.delete(user)
    db.commit()
    return Response(status_code=204)