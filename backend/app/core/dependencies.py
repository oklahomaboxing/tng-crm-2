from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import User


def current_user(
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

    return user