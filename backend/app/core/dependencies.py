import re
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
    from app.managers.access import authorize_workspace_request
    authorize_workspace_request(db,user,payload,request)
    if user.role == 'event_coordinator':
        path=request.url.path
        allowed=path in {'/api/me','/api/auth/remember-device','/api/auth/forget-device','/api/auth/logout','/api/auth/devices'} or path.startswith('/api/auth/security/') or path.startswith('/api/auth/devices/') or path.startswith('/api/venue/')
        if not allowed:raise HTTPException(403,'This account is restricted to facility bookings and account security')
    if user.role in {"investor", "sponsor", "concessions"}:
        path = request.url.path
        allowed = path in {"/api/partners/portal", "/api/me", "/api/auth/remember-device", "/api/auth/forget-device", "/api/auth/logout", "/api/auth/devices"} or path.startswith("/api/auth/security/") or path.startswith("/api/auth/devices/")
        allowed = allowed or (user.role in {"investor","sponsor"} and request.method=="GET" and bool(re.fullmatch(r"/api/partners/events/[0-9]+/cost-statement(?:\.pdf)?",path)))
        allowed = allowed or (user.role == "concessions" and (path == "/api/concessions/events" or path.startswith("/api/concessions/events/")))
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
