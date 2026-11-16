from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import User


def current_user(
    request: Request,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing token",
        )

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if not user.active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive",
        )

    from app.account_security import valid_session
    if not valid_session(payload, user, db):
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    if user.role in {"investor", "sponsor", "concessions"}:
        path = request.url.path
        allowed = path in {"/api/partners/portal", "/api/me", "/api/auth/remember-device", "/api/auth/forget-device", "/api/auth/logout", "/api/auth/devices"} or path.startswith("/api/auth/security/") or path.startswith("/api/auth/devices/")
        if not allowed:
            raise HTTPException(status_code=403, detail="This partner account can access only its portal and account security")
    return user


def staff_user(user: User = Depends(current_user)) -> User:
    """Require an active operations account, including on router-level guards."""
    if user.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="Admin or staff access required")
    return user


def sales_user(user: User = Depends(current_user)) -> User:
    if user.role not in {"admin", "staff", "rep"}:
        raise HTTPException(status_code=403, detail="Sales access required")
    return user
