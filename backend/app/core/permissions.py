from fastapi import HTTPException

from app.models import User


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin only",
        )


def require_admin_or_staff(user: User) -> None:
    if user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Admin or staff access required",
        )