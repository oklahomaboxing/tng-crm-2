import resend
import httpx
import os
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header, Request, UploadFile, File, Response
from sqlalchemy.orm import Session

from ..database import Base, engine, get_db
from ..models import User, Member
from ..auth import hash_password, decode_token
from .models import MemberAccount, MemberInvite, InBodyScan, MemberProfilePhoto
from .schemas import ActivateMemberIn, InviteMemberIn, LinkInBodyIn, ManualInBodyScanIn

# The main project currently creates tables before feature routers are loaded.
# This makes the new feature safe to install without an Alembic migration.
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api/member", tags=["Member Portal"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: User):
    if user.role not in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Admin/staff only")


def member_account_for_user(db: Session, user: User) -> MemberAccount:
    account = db.query(MemberAccount).filter(MemberAccount.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=403, detail="Member account not linked")
    return account


@router.get("/admin/{member_id}/invite-status")
def member_invite_status(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    account = (
        db.query(MemberAccount)
        .filter(MemberAccount.member_id == member_id)
        .first()
    )

    if account:
        return {
            "status": "active",
            "activated": True,
            "invite_pending": False,
            "message": "Member login is active.",
        }

    active_invite = (
        db.query(MemberInvite)
        .filter(
            MemberInvite.member_id == member_id,
            MemberInvite.used_at == None,
            MemberInvite.expires_at > datetime.utcnow(),
        )
        .order_by(MemberInvite.created_at.desc())
        .first()
    )

    if active_invite:
        return {
            "status": "invite_sent",
            "activated": False,
            "invite_pending": True,
            "email": member.email,
            "sent_at": active_invite.created_at,
            "expires_at": active_invite.expires_at,
            "message": "Activation email already sent.",
        }

    return {
        "status": "not_invited",
        "activated": False,
        "invite_pending": False,
        "email": member.email,
        "message": "Member login has not been activated.",
    }

@router.post("/admin/invite")
def create_member_invite(
    data: InviteMemberIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if not (member.email or "").strip():
        raise HTTPException(status_code=400, detail="Member needs an email address")

    existing_account = db.query(MemberAccount).filter(MemberAccount.member_id == member.id).first()
    if existing_account:
        raise HTTPException(status_code=409, detail="Member account already activated")

    active_invite = (
        db.query(MemberInvite)
        .filter(
            MemberInvite.member_id == member.id,
            MemberInvite.used_at == None,
            MemberInvite.expires_at > datetime.utcnow(),
        )
        .order_by(MemberInvite.created_at.desc())
        .first()
    )

    if active_invite:
        return {
            "member_id": member.id,
            "email": member.email,
            "already_sent": True,
            "email_sent": False,
            "message": "Activation email has already been sent. A new invitation cannot be sent until the current 7-day invitation expires.",
            "expires_at": active_invite.expires_at,
        }

    raw_token = secrets.token_urlsafe(32)
    invite = MemberInvite(
        member_id=member.id,
        token_hash=_token_hash(raw_token),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()

    activation_path = f"/member/activate?token={raw_token}"
    frontend_url = os.getenv(
        "FRONTEND_URL",
        "https://tngos.tngboxinggym.com",
    ).rstrip("/")
    activation_url = f"{frontend_url}{activation_path}"

    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv(
        "RESEND_FROM_EMAIL",
        "TNG Boxing <marketing@tngboxinggym.com>",
    )

    email_sent = False
    email_error = None

    if resend_api_key:
        try:
            resend.api_key = resend_api_key

            resend.Emails.send(
                {
                    "from": sender_email,
                    "to": [member.email],
                    "subject": "Activate Your TNG Boxing Member Account",
                    "html": f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
                      <h2>Welcome to TNG Boxing</h2>

                      <p>Your TNG Boxing member account is ready.</p>

                      <p>
                        Use the button below to create your password and activate
                        access to your member portal.
                      </p>

                      <p style="margin:30px 0;">
                        <a
                          href="{activation_url}"
                          style="
                            background:#d71920;
                            color:#ffffff;
                            padding:14px 22px;
                            text-decoration:none;
                            border-radius:6px;
                            font-weight:bold;
                          "
                        >
                          Activate My Account
                        </a>
                      </p>

                      <p>This activation link expires in 7 days.</p>

                      <p>
                        After activation, sign in at
                        <strong>tngos.tngboxinggym.com</strong>
                        using your email and new password.
                      </p>

                      <p><strong>TNG Boxing — Earned Not Given</strong></p>
                    </div>
                    """,
                }
            )

            email_sent = True

        except Exception as exc:
            email_error = str(exc)

    else:
        email_error = "RESEND_API_KEY is not configured"

    return {
        "member_id": member.id,
        "email": member.email,
        "activation_token": raw_token,
        "activation_path": activation_path,
        "activation_url": activation_url,
        "expires_at": invite.expires_at,
        "email_sent": email_sent,
        "email_error": email_error,
    }


@router.post("/activate")
def activate_member(data: ActivateMemberIn, db: Session = Depends(get_db)):
    invite = (
        db.query(MemberInvite)
        .filter(MemberInvite.token_hash == _token_hash(data.token))
        .first()
    )
    if not invite or invite.used_at is not None or invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Activation link is invalid or expired")

    member = db.query(Member).filter(Member.id == invite.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    email = (member.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Member does not have an email address")

    user = db.query(User).filter(User.email == email).first()
    if user and user.role != "member":
        raise HTTPException(
            status_code=409,
            detail="That email is already used by a non-member TNGOS account",
        )

    if not user:
        user = User(
            name=f"{member.first_name} {member.last_name}".strip(),
            email=email,
            password_hash=hash_password(data.password),
            role="member",
        )
        db.add(user)
        db.flush()
    else:
        user.password_hash = hash_password(data.password)
        user.role = "member"

    existing = db.query(MemberAccount).filter(MemberAccount.member_id == member.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Member account already activated")

    account = MemberAccount(member_id=member.id, user_id=user.id)
    db.add(account)
    invite.used_at = datetime.utcnow()
    db.commit()

    return {
        "ok": True,
        "message": "Member account activated. You can now sign in with your email and password.",
    }



@router.get("/me/photo")
def member_profile_photo(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = member_account_for_user(db, user)

    photo = (
        db.query(MemberProfilePhoto)
        .filter(
            MemberProfilePhoto.member_id
            == account.member_id
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Profile photo not found.",
        )

    return Response(
        content=photo.file_data,
        media_type=photo.content_type,
        headers={
            "Cache-Control": "private, max-age=300"
        },
    )


@router.post("/me/photo")
async def upload_member_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = member_account_for_user(db, user)

    member = (
        db.query(Member)
        .filter(Member.id == account.member_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member profile not found.",
        )

    file_name = str(
        file.filename or "profile-photo"
    ).strip()

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded photo is empty.",
        )

    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Profile photo must be 5 MB or smaller.",
        )

    detected_type = None

    if contents.startswith(b"\xff\xd8\xff"):
        detected_type = "image/jpeg"

    elif contents.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_type = "image/png"

    elif (
        len(contents) >= 12
        and contents[0:4] == b"RIFF"
        and contents[8:12] == b"WEBP"
    ):
        detected_type = "image/webp"

    if not detected_type:
        raise HTTPException(
            status_code=400,
            detail="Photo must be JPG, PNG, or WEBP.",
        )

    photo = (
        db.query(MemberProfilePhoto)
        .filter(
            MemberProfilePhoto.member_id
            == member.id
        )
        .first()
    )

    if not photo:
        photo = MemberProfilePhoto(
            member_id=member.id,
        )
        db.add(photo)

    photo.file_name = file_name
    photo.content_type = detected_type
    photo.file_size = len(contents)
    photo.file_data = contents
    photo.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "message": "Profile photo updated.",
        "photo_url": "/api/member/me/photo",
    }


@router.delete("/me/photo")
def delete_member_profile_photo(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = member_account_for_user(db, user)

    photo = (
        db.query(MemberProfilePhoto)
        .filter(
            MemberProfilePhoto.member_id
            == account.member_id
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Profile photo not found.",
        )

    db.delete(photo)
    db.commit()

    return {
        "ok": True,
        "message": "Profile photo removed.",
    }


@router.get("/me")
def member_me(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = member_account_for_user(db, user)
    member = db.query(Member).filter(Member.id == account.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member profile not found")

    profile_photo = (
        db.query(MemberProfilePhoto)
        .filter(
            MemberProfilePhoto.member_id
            == member.id
        )
        .first()
    )

    latest_scan = (
        db.query(InBodyScan)
        .filter(InBodyScan.member_id == member.id)
        .order_by(InBodyScan.scan_date.desc())
        .first()
    )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "member": {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "phone": member.phone,
            "member_number": member.member_number,
            "digital_member_id": member.digital_member_id,
            "barcode": member.barcode,
            "qr_code": member.qr_code,
            "membership_start": member.membership_start,
            "membership_end": member.membership_end,
            "membership_status": member.membership_status,
            "membership_type": member.membership_type,
            "membership_level": member.membership_level,
            "waiver_signed": member.waiver_signed,
            "assigned_coach": member.assigned_coach,
            "last_checkin": member.last_checkin,
            "total_checkins": member.total_checkins,
            "billing_cycle": member.billing_cycle,
            "monthly_rate": member.monthly_rate,
            "next_billing_date": member.next_billing_date,
            "autopay_enabled": member.autopay_enabled,
            "billing_status": member.billing_status,
            "photo_url": (
                "/api/member/me/photo"
                if profile_photo
                else member.photo_url
            ),
        },
        "inbody": {
            "linked": bool(account.inbody_user_id),
            "inbody_user_id": account.inbody_user_id,
            "consent": account.member_consent_inbody,
            "last_synced_at": account.inbody_last_synced_at,
            "latest_scan": serialize_scan(latest_scan) if latest_scan else None,
        },
    }


def serialize_scan(s: InBodyScan):
    return {
        "id": s.id,
        "scan_date": s.scan_date,
        "weight": s.weight,
        "skeletal_muscle_mass": s.skeletal_muscle_mass,
        "body_fat_mass": s.body_fat_mass,
        "percent_body_fat": s.percent_body_fat,
        "bmi": s.bmi,
        "visceral_fat_level": s.visceral_fat_level,
        "bmr": s.bmr,
        "inbody_score": s.inbody_score,
        "source": s.source,
    }




def _inbody_result_config():
    return {
        "api_key": os.getenv("INBODY_API_KEY", "").strip(),
        "account": os.getenv("INBODY_ACCOUNT", "").strip(),
        "result_url": os.getenv("INBODY_RESULT_URL", "").strip(),
    }


def _inbody_response_shape(value, depth=0):
    """
    Return field names / structure only.
    Never return health measurement values.
    """
    if depth > 3:
        return "..."

    if isinstance(value, dict):
        return {
            str(key): _inbody_response_shape(child, depth + 1)
            for key, child in list(value.items())[:50]
        }

    if isinstance(value, list):
        if not value:
            return []

        return [
            _inbody_response_shape(value[0], depth + 1)
        ]

    return type(value).__name__


async def _fetch_inbody_result(
    user_token: str,
    test_datetime: str,
):
    config = _inbody_result_config()

    missing = [
        key
        for key, value in config.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing InBody configuration: "
            + ", ".join(missing)
        )

    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"],
        "Account": config["account"],
    }

    body = {
        "UserToken": user_token,
        "Datetimes": test_datetime,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            config["result_url"],
            headers=headers,
            json=body,
        )

    response.raise_for_status()

    try:
        return response.json()
    except Exception as exc:
        raise RuntimeError(
            "InBody result API did not return JSON"
        ) from exc


@router.post("/inbody/webhook")
async def inbody_webhook(request: Request):
    """
    LookinBody Web -> TNGOS callback.

    InBody can be configured with a custom webhook header.
    We use X-TNG-InBody-Webhook and compare it to an
    environment variable stored securely on the backend.
    """
    expected_secret = os.getenv("INBODY_WEBHOOK_SECRET", "").strip()

    if not expected_secret:
        raise HTTPException(
            status_code=503,
            detail="InBody webhook is not configured",
        )

    supplied_secret = request.headers.get(
        "X-TNG-InBody-Webhook",
        "",
    ).strip()

    if supplied_secret != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook credentials",
        )

    # Parse incoming JSON without logging the body because
    # it may contain member health/body-composition information.
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be a JSON object",
        )

    # LookinBody webhook identifiers.
    # UserID = member ID stored in LookinBody Web.
    # TelHP = UserToken / mobile phone identifier.
    user_id = str(payload.get("UserID") or "").strip()
    user_token = str(payload.get("TelHP") or "").strip()
    test_datetime = str(
        payload.get("TestDatetimes") or ""
    ).strip()

    is_temp_raw = str(
        payload.get("IsTempData") or ""
    ).strip().lower()

    is_temp = is_temp_raw in {
        "true",
        "1",
        "yes",
        "y",
    }

    # Temporary measurements are not available through the
    # result API until reviewed/corrected in LookinBody Web.
    if is_temp:
        return {
            "ok": True,
            "received": True,
            "status": "temporary_data_ignored",
            "user_id_present": bool(user_id),
            "user_token_present": bool(user_token),
            "test_datetime_present": bool(test_datetime),
        }

    if not user_id and not user_token:
        raise HTTPException(
            status_code=400,
            detail="Webhook contains no UserID or UserToken",
        )

    config = _inbody_result_config()

    if not all(config.values()):
        return {
            "ok": True,
            "received": True,
            "status": "result_sync_not_configured",
            "user_id_present": bool(user_id),
            "user_token_present": bool(user_token),
            "test_datetime_present": bool(test_datetime),
        }

    # The documented GetInBodyData request uses UserToken
    # (TelHP) and Datetimes.
    if not user_token or not test_datetime:
        return {
            "ok": True,
            "received": True,
            "status": "result_sync_missing_identifier",
            "user_id_present": bool(user_id),
            "user_token_present": bool(user_token),
            "test_datetime_present": bool(test_datetime),
        }

    try:
        result = await _fetch_inbody_result(
            user_token=user_token,
            test_datetime=test_datetime,
        )
    except httpx.HTTPStatusError as exc:
        # Always acknowledge the webhook so InBody does not
        # treat a result-API permission issue as a webhook failure.
        return {
            "ok": True,
            "received": True,
            "status": "result_sync_pending",
            "result_api_status": exc.response.status_code,
            "user_id_present": bool(user_id),
            "user_token_present": bool(user_token),
            "test_datetime_present": bool(test_datetime),
        }
    except (httpx.RequestError, RuntimeError):
        return {
            "ok": True,
            "received": True,
            "status": "result_sync_pending",
            "user_id_present": bool(user_id),
            "user_token_present": bool(user_token),
            "test_datetime_present": bool(test_datetime),
        }

    return {
        "ok": True,
        "received": True,
        "status": "result_received",
        "user_id_present": bool(user_id),
        "user_token_present": bool(user_token),
        "test_datetime_present": bool(test_datetime),
        "result_shape": _inbody_response_shape(result),
    }


@router.get("/inbody/scans")
def my_inbody_scans(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = member_account_for_user(db, user)
    scans = (
        db.query(InBodyScan)
        .filter(InBodyScan.member_id == account.member_id)
        .order_by(InBodyScan.scan_date.asc())
        .all()
    )
    return [serialize_scan(x) for x in scans]


@router.post("/admin/{member_id}/inbody/link")
def link_inbody(
    member_id: int,
    data: LinkInBodyIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)
    account = db.query(MemberAccount).filter(MemberAccount.member_id == member_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Member account has not been activated")
    account.inbody_user_id = data.inbody_user_id.strip()
    account.member_consent_inbody = data.consent
    account.inbody_linked_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "member_id": member_id, "inbody_user_id": account.inbody_user_id}


@router.post("/admin/{member_id}/inbody/scans")
def add_manual_scan(
    member_id: int,
    data: ManualInBodyScanIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    scan = InBodyScan(
        member_id=member_id,
        scan_date=data.scan_date,
        weight=data.weight,
        skeletal_muscle_mass=data.skeletal_muscle_mass,
        body_fat_mass=data.body_fat_mass,
        percent_body_fat=data.percent_body_fat,
        bmi=data.bmi,
        visceral_fat_level=data.visceral_fat_level,
        bmr=data.bmr,
        inbody_score=data.inbody_score,
        source="manual",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return serialize_scan(scan)




