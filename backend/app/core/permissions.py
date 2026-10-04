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


def require_matchmaker_access(user: User) -> None:
    """
    Boxing operations access.

    Admin/staff retain full access.
    Matchmakers may manage matchmaking operations without receiving
    unrelated CRM/admin permissions.
    """
    if user.role not in {"admin", "staff", "matchmaker"}:
        raise HTTPException(
            status_code=403,
            detail="Matchmaker access required",
        )


def require_manager_access(user: User) -> None:
    """
    Manager portal access.

    Admin/staff may administrate manager records, while a manager
    account may access only manager-scoped routes.
    """
    if user.role not in {"admin", "staff", "manager"}:
        raise HTTPException(
            status_code=403,
            detail="Manager access required",
        )


def require_boxing_portal_access(user: User) -> None:
    """
    Shared boxing workflow access for routes intentionally available
    to boxing operations and manager users.
    """
    if user.role not in {
        "admin",
        "staff",
        "matchmaker",
        "manager",
    }:
        raise HTTPException(
            status_code=403,
            detail="Boxing portal access required",
        )
