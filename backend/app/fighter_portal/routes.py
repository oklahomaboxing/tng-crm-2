import json
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import LETTER
import hashlib
import os
import secrets
import base64
import io
import qrcode
from datetime import datetime, timedelta

import resend
from fastapi import Request, APIRouter, Depends, Header, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session

from ..auth import decode_token, hash_password
from ..database import Base, engine, get_db
from ..models import User
from ..matchmaker.models import (
    BoxingFighter,
    BoxingEvent,
    BoxingBout,
    BoxingContract, BoxingSignedContractDocument,
    BoxingContractSignature,
)
from ..ticketing.models import EventSeller, IssuedTicket, SellerPayout
from .models import FighterAccount, FighterInvite, FighterPhoto
from .schemas import ActivateFighterIn, InviteFighterIn


Base.metadata.create_all(bind=engine)

router = APIRouter(
    prefix="/api/fighter",
    tags=["Fighter Portal"],
)


def _contract_signature_snapshot(contract):
    """
    Authoritative server-side snapshot of every material
    term used by the official fighter contract.
    """
    snapshot = {
        "template_version":
            "oklahoma-boxing-contract-v1",
        "contract_id":
            contract.id,
        "event_id":
            contract.event_id,
        "bout_id":
            contract.bout_id,
        "fighter_id":
            contract.fighter_id,
        "opponent_id":
            contract.opponent_id,
        "corner":
            contract.corner,
        "contract_date":
            contract.contract_date,
        "boxer_name":
            contract.boxer_name,
        "boxer_federal_id":
            contract.boxer_federal_id,
        "boxer_address":
            contract.boxer_address,
        "boxer_phone":
            contract.boxer_phone,
        "boxer_manager":
            contract.boxer_manager,
        "opponent_name":
            contract.opponent_name,
        "rounds":
            contract.rounds,
        "maximum_weight":
            contract.maximum_weight,
        "event_name":
            contract.event_name,
        "event_date":
            contract.event_date,
        "venue":
            contract.venue,
        "venue_address":
            contract.venue_address,
        "promoter_name":
            contract.promoter_name,
        "promoter_address":
            contract.promoter_address,
        "promoter_phone":
            contract.promoter_phone,
        "promoter_matchmaker":
            contract.promoter_matchmaker,
        "gross_purse":
            contract.gross_purse,
        "travel_type":
            getattr(
                contract,
                "travel_type",
                "",
            ),
        "travel_paid_by":
            getattr(
                contract,
                "travel_paid_by",
                "",
            ),
        "travel_expense":
            contract.travel_expense,
        "hotel_provided":
            getattr(
                contract,
                "hotel_provided",
                "",
            ),
        "hotel_name":
            getattr(
                contract,
                "hotel_name",
                "",
            ),
        "hotel_nights":
            getattr(
                contract,
                "hotel_nights",
                0,
            ),
        "per_diem_daily":
            getattr(
                contract,
                "per_diem_daily",
                0,
            ),
        "per_diem_days":
            getattr(
                contract,
                "per_diem_days",
                0,
            ),
        "per_diem_total":
            getattr(
                contract,
                "per_diem_total",
                0,
            ),
        "deductions":
            contract.deductions,
        "boxer_paid":
            contract.boxer_paid,
        "additional_terms":
            contract.additional_terms,
        "cancellation_pay":
            contract.cancellation_pay,
    }

    # Stable JSON means the same terms always produce
    # the same hash.
    snapshot_json = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    snapshot_hash = hashlib.sha256(
        snapshot_json.encode("utf-8")
    ).hexdigest()

    return snapshot_json, snapshot_hash


def _linked_fighter_account(
    user,
    db: Session,
):
    account = (
        db.query(FighterAccount)
        .filter(
            FighterAccount.user_id
            == user.id
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=403,
            detail=(
                "This login is not linked "
                "to a fighter account."
            ),
        )

    fighter = (
        db.query(BoxingFighter)
        .filter(
            BoxingFighter.id
            == account.fighter_id
        )
        .first()
    )

    if not fighter:
        raise HTTPException(
            status_code=404,
            detail="Linked fighter profile not found.",
        )

    return account, fighter


def _token_hash(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing token",
        )

    payload = decode_token(
        authorization.split(" ", 1)[1]
    )

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = (
        db.query(User)
        .filter(
            User.id == int(payload["sub"])
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


def require_admin(user: User):
    if user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=403,
            detail="Admin/staff only",
        )


def fighter_account_for_user(
    db: Session,
    user: User,
) -> FighterAccount:

    if user.role != "fighter":
        raise HTTPException(
            status_code=403,
            detail="Fighter account required",
        )

    account = (
        db.query(FighterAccount)
        .filter(
            FighterAccount.user_id == user.id
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=403,
            detail="Fighter account not linked",
        )

    return account


@router.get(
    "/admin/{fighter_id}/invite-status"
)
def fighter_invite_status(
    fighter_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    fighter = (
        db.query(BoxingFighter)
        .filter(
            BoxingFighter.id == fighter_id
        )
        .first()
    )

    if not fighter:
        raise HTTPException(
            status_code=404,
            detail="Fighter not found",
        )

    account = (
        db.query(FighterAccount)
        .filter(
            FighterAccount.fighter_id
            == fighter_id
        )
        .first()
    )

    if account:
        return {
            "status": "active",
            "activated": True,
            "invite_pending": False,
            "fighter_id": fighter.id,
            "email": fighter.email,
            "message": (
                "Fighter login is active."
            ),
        }

    active_invite = (
        db.query(FighterInvite)
        .filter(
            FighterInvite.fighter_id
            == fighter_id,
            FighterInvite.used_at == None,
            FighterInvite.expires_at
            > datetime.utcnow(),
        )
        .order_by(
            FighterInvite.created_at.desc()
        )
        .first()
    )

    if active_invite:
        return {
            "status": "invite_sent",
            "activated": False,
            "invite_pending": True,
            "fighter_id": fighter.id,
            "email": fighter.email,
            "sent_at": active_invite.created_at,
            "expires_at": (
                active_invite.expires_at
            ),
            "message": (
                "Fighter activation email "
                "already sent."
            ),
        }

    return {
        "status": "not_invited",
        "activated": False,
        "invite_pending": False,
        "fighter_id": fighter.id,
        "email": fighter.email,
        "message": (
            "Fighter login has not been "
            "activated."
        ),
    }


@router.post("/admin/invite")
def create_fighter_invite(
    data: InviteFighterIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    fighter = (
        db.query(BoxingFighter)
        .filter(
            BoxingFighter.id
            == data.fighter_id
        )
        .first()
    )

    if not fighter:
        raise HTTPException(
            status_code=404,
            detail="Fighter not found",
        )

    email = (
        fighter.email or ""
    ).strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail=(
                "Fighter needs an email "
                "address"
            ),
        )

    existing_account = (
        db.query(FighterAccount)
        .filter(
            FighterAccount.fighter_id
            == fighter.id
        )
        .first()
    )

    if existing_account:
        raise HTTPException(
            status_code=409,
            detail=(
                "Fighter account already "
                "activated"
            ),
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if (
        existing_user
        and existing_user.role
        != "fighter"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "That email is already used "
                "by another TNGOS account"
            ),
        )

    active_invite = (
        db.query(FighterInvite)
        .filter(
            FighterInvite.fighter_id
            == fighter.id,
            FighterInvite.used_at == None,
            FighterInvite.expires_at
            > datetime.utcnow(),
        )
        .order_by(
            FighterInvite.created_at.desc()
        )
        .first()
    )

    if active_invite:
        # Invalidate the old invite so a fresh activation
        # token can be issued immediately.
        active_invite.expires_at = datetime.utcnow()
        db.commit()

    raw_token = secrets.token_urlsafe(32)

    invite = FighterInvite(
        fighter_id=fighter.id,
        token_hash=_token_hash(raw_token),
        expires_at=(
            datetime.utcnow()
            + timedelta(days=7)
        ),
    )

    db.add(invite)
    db.commit()

    activation_path = (
        "/fighter/activate"
        f"?token={raw_token}"
    )

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "https://tngos.tngboxinggym.com",
    ).rstrip("/")

    activation_url = (
        f"{frontend_url}{activation_path}"
    )

    resend_api_key = os.getenv(
        "RESEND_API_KEY"
    )

    sender_email = os.getenv(
        "RESEND_FROM_EMAIL",
        (
            "TNG Boxing "
            "<marketing@tngboxinggym.com>"
        ),
    )

    email_sent = False
    email_error = None

    if resend_api_key:
        try:
            resend.api_key = resend_api_key

            resend.Emails.send(
                {
                    "from": sender_email,
                    "to": [email],
                    "subject": (
                        "Activate Your TNG "
                        "Fighter Portal"
                    ),
                    "html": f"""
                    <div
                      style="
                        font-family:Arial,sans-serif;
                        max-width:600px;
                        margin:auto;
                      "
                    >
                      <h2>
                        Welcome to the
                        TNG Fighter Portal
                      </h2>

                      <p>
                        Hello
                        <strong>
                          {fighter.legal_name}
                        </strong>,
                      </p>

                      <p>
                        Your TNG fighter account
                        is ready.
                      </p>

                      <p>
                        Use the button below to
                        create your password and
                        activate your Fighter
                        Portal access.
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
                          Activate Fighter Portal
                        </a>
                      </p>

                      <p>
                        This activation link
                        expires in 7 days.
                      </p>

                      <p>
                        Your Fighter Portal will
                        give you access to your
                        fight information,
                        contracts, medical
                        requirements, ticket
                        sales and commissions.
                      </p>

                      <p>
                        After activation, sign in
                        at
                        <strong>
                          tngos.tngboxinggym.com
                        </strong>
                        using your email and
                        password.
                      </p>

                      <p>
                        <strong>
                          TNG Boxing —
                          Earned Not Given
                        </strong>
                      </p>
                    </div>
                    """,
                }
            )

            email_sent = True

        except Exception as exc:
            email_error = str(exc)

    else:
        email_error = (
            "RESEND_API_KEY is not "
            "configured"
        )

    return {
        "fighter_id": fighter.id,
        "email": email,
        "activation_token": raw_token,
        "activation_path": activation_path,
        "activation_url": activation_url,
        "expires_at": invite.expires_at,
        "email_sent": email_sent,
        "email_error": email_error,
    }


@router.post("/activate")
def activate_fighter(
    data: ActivateFighterIn,
    db: Session = Depends(get_db),
):
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match",
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be at least "
                "8 characters"
            ),
        )

    invite = (
        db.query(FighterInvite)
        .filter(
            FighterInvite.token_hash
            == _token_hash(data.token)
        )
        .first()
    )

    if (
        not invite
        or invite.used_at is not None
        or invite.expires_at
        < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Activation link is invalid "
                "or expired"
            ),
        )

    fighter = (
        db.query(BoxingFighter)
        .filter(
            BoxingFighter.id
            == invite.fighter_id
        )
        .first()
    )

    if not fighter:
        raise HTTPException(
            status_code=404,
            detail="Fighter not found",
        )

    email = (
        fighter.email or ""
    ).strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail=(
                "Fighter does not have "
                "an email address"
            ),
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if (
        user
        and user.role != "fighter"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "That email is already used "
                "by a non-fighter TNGOS "
                "account"
            ),
        )

    if not user:
        user = User(
            name=fighter.legal_name,
            email=email,
            password_hash=hash_password(
                data.password
            ),
            role="fighter",
            active=True,
        )

        db.add(user)
        db.flush()

    else:
        user.name = fighter.legal_name
        user.password_hash = hash_password(
            data.password
        )
        user.role = "fighter"
        user.active = True

    existing = (
        db.query(FighterAccount)
        .filter(
            FighterAccount.fighter_id
            == fighter.id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "Fighter account already "
                "activated"
            ),
        )

    account = FighterAccount(
        fighter_id=fighter.id,
        user_id=user.id,
    )

    db.add(account)

    invite.used_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "fighter_id": fighter.id,
        "message": (
            "Fighter account activated. "
            "You can now sign in with your "
            "email and password."
        ),
    }




@router.get("/me/contracts")
def my_contracts(
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    contracts = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.fighter_id
            == fighter.id
        )
        .order_by(
            BoxingContract.id.desc()
        )
        .all()
    )

    contract_ids = [
        row.id
        for row in contracts
    ]

    documents = {}

    if contract_ids:
        document_rows = (
            db.query(
                BoxingSignedContractDocument
            )
            .filter(
                BoxingSignedContractDocument.contract_id.in_(
                    contract_ids
                )
            )
            .all()
        )

        documents = {
            row.contract_id: row
            for row in document_rows
        }

    return {
        "fighter_id": fighter.id,
        "contracts": [
            {
                "contract_id": row.id,
                "event_id": row.event_id,
                "bout_id": row.bout_id,
                "status": row.status,
                "contract_date":
                    row.contract_date,
                "boxer_name":
                    row.boxer_name,
                "boxer_federal_id":
                    row.boxer_federal_id,
                "boxer_address":
                    row.boxer_address,
                "boxer_phone":
                    row.boxer_phone,
                "boxer_manager":
                    row.boxer_manager,
                "promoter_name":
                    row.promoter_name,
                "promoter_address":
                    row.promoter_address,
                "promoter_phone":
                    row.promoter_phone,
                "promoter_matchmaker":
                    row.promoter_matchmaker,
                "event_name":
                    row.event_name,
                "event_date":
                    row.event_date,
                "venue":
                    row.venue,
                "venue_address":
                    row.venue_address,
                "opponent_name":
                    row.opponent_name,
                "rounds":
                    row.rounds,
                "maximum_weight":
                    row.maximum_weight,
                "gross_purse":
                    row.gross_purse,
                "deductions":
                    row.deductions,
                "cancellation_pay":
                    row.cancellation_pay,
                "travel_type":
                    getattr(
                        row,
                        "travel_type",
                        "",
                    ),
                "travel_paid_by":
                    getattr(
                        row,
                        "travel_paid_by",
                        "",
                    ),
                "travel_expense":
                    row.travel_expense,
                "hotel_provided":
                    getattr(
                        row,
                        "hotel_provided",
                        "",
                    ),
                "hotel_name":
                    getattr(
                        row,
                        "hotel_name",
                        "",
                    ),
                "hotel_nights":
                    getattr(
                        row,
                        "hotel_nights",
                        0,
                    ),
                "per_diem_daily":
                    getattr(
                        row,
                        "per_diem_daily",
                        0,
                    ),
                "per_diem_days":
                    getattr(
                        row,
                        "per_diem_days",
                        0,
                    ),
                "per_diem_total":
                    getattr(
                        row,
                        "per_diem_total",
                        0,
                    ),
                "boxer_paid":
                    row.boxer_paid,
                "additional_terms":
                    row.additional_terms,
                "signed_document":
                    row.id in documents,
                "signed_file_name":
                    (
                        documents[row.id].file_name
                        if row.id in documents
                        else None
                    ),
                "signed_uploaded_at":
                    (
                        documents[row.id].uploaded_at
                        if row.id in documents
                        else None
                    ),
            }
            for row in contracts
        ],
    }


@router.post(
    "/me/contracts/{contract_id}/esign"
)
def fighter_esign_contract(
    contract_id: int,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    contract = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.id == contract_id,
            BoxingContract.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    current_status = str(
        contract.status or ""
    ).strip().lower()

    if current_status not in (
        "accepted",
        "generated",
        "sent",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "This contract is not currently "
                "eligible for electronic signature."
            ),
        )

    typed_name = str(
        data.get("typed_legal_name") or ""
    ).strip()

    agreed = bool(
        data.get("agreed")
    )

    if not typed_name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Type your legal name to sign "
                "the contract."
            ),
        )

    fighter_name = str(
        fighter.legal_name or ""
    ).strip()

    if fighter_name:
        normalize = lambda value: " ".join(
            str(value)
            .lower()
            .replace(".", "")
            .replace(",", "")
            .split()
        )

        if normalize(typed_name) != normalize(
            fighter_name
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Typed legal name must match "
                    "your fighter profile."
                ),
            )

    if not agreed:
        raise HTTPException(
            status_code=400,
            detail=(
                "You must agree to the contract "
                "before signing."
            ),
        )

    existing = (
        db.query(BoxingContractSignature)
        .filter(
            BoxingContractSignature.contract_id
            == contract.id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "This contract has already been "
                "electronically signed."
            ),
        )

    snapshot_json, snapshot_hash = (
        _contract_signature_snapshot(
            contract
        )
    )

    forwarded_for = (
        request.headers.get(
            "x-forwarded-for",
            "",
        )
        or ""
    )

    signer_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (
            request.client.host
            if request.client
            else ""
        )
    )

    signature = BoxingContractSignature(
        contract_id=contract.id,
        fighter_id=fighter.id,
        signer_user_id=user.id,
        typed_legal_name=typed_name,
        agreed=True,
        template_version=(
            "oklahoma-boxing-contract-v1"
        ),
        contract_snapshot=snapshot_json,
        snapshot_sha256=snapshot_hash,
        signer_ip=signer_ip,
        signer_user_agent=(
            request.headers.get(
                "user-agent",
                "",
            )
            or ""
        )[:2000],
    )

    db.add(signature)

    contract.status = "signed"

    db.commit()
    db.refresh(signature)

    return {
        "ok": True,
        "contract_id": contract.id,
        "status": contract.status,
        "signed_at": signature.signed_at,
        "typed_legal_name":
            signature.typed_legal_name,
        "snapshot_sha256":
            signature.snapshot_sha256,
        "template_version":
            signature.template_version,
        "message": (
            "Contract electronically signed."
        ),
    }


@router.post(
    "/me/contracts/{contract_id}/signed-upload"
)
async def fighter_upload_signed_contract(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    # SECURITY:
    # Contract must belong to the fighter linked
    # to the current logged-in user.
    contract = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.id == contract_id,
            BoxingContract.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    file_name = str(
        file.filename
        or "signed-contract.pdf"
    ).strip()

    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Signed contract must be a PDF."
            ),
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    max_size = 10 * 1024 * 1024

    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail=(
                "Signed contract PDF must be "
                "10 MB or smaller."
            ),
        )

    if not contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file is not "
                "a valid PDF."
            ),
        )

    document = (
        db.query(
            BoxingSignedContractDocument
        )
        .filter(
            BoxingSignedContractDocument.contract_id
            == contract.id
        )
        .first()
    )

    if not document:
        document = (
            BoxingSignedContractDocument(
                contract_id=contract.id,
            )
        )
        db.add(document)

    document.file_name = file_name
    document.content_type = (
        "application/pdf"
    )
    document.file_size = len(contents)
    document.file_data = contents
    document.source = "fighter_upload"

    document.uploaded_by_user_id = user.id
    document.uploaded_by_name = (
        fighter.legal_name
        or getattr(user, "name", "")
        or getattr(user, "email", "")
        or ""
    )

    document.uploaded_at = datetime.utcnow()
    document.updated_at = datetime.utcnow()

    # Uploading the signed agreement advances
    # the contract lifecycle to signed.
    contract.status = "signed"
    contract.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(document)
    db.refresh(contract)

    return {
        "ok": True,
        "contract_id": contract.id,
        "status": contract.status,
        "signed_document": True,
        "file_name": document.file_name,
        "uploaded_at":
            document.uploaded_at,
        "message": (
            "Signed contract uploaded "
            "successfully."
        ),
    }


@router.get(
    "/me/contracts/{contract_id}/signed-file"
)
def fighter_download_signed_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    # SECURITY:
    # No fighter_id comes from the browser.
    # Ownership is derived from the login.
    contract = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.id == contract_id,
            BoxingContract.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    document = (
        db.query(
            BoxingSignedContractDocument
        )
        .filter(
            BoxingSignedContractDocument.contract_id
            == contract.id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail=(
                "No signed contract has "
                "been uploaded yet."
            ),
        )

    safe_name = (
        document.file_name
        or (
            f"contract-{contract.id}"
            "-signed.pdf"
        )
    ).replace('"', "")

    return Response(
        content=document.file_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                (
                    'attachment; filename="'
                    f'{safe_name}"'
                ),
            "Cache-Control":
                "private, no-store, max-age=0",
            "X-Content-Type-Options":
                "nosniff",
        },
    )


@router.get("/me/fight-offers")
def fighter_fight_offers(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = fighter_account_for_user(
        db,
        user,
    )

    contracts = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.fighter_id
            == account.fighter_id
        )
        .order_by(
            BoxingContract.created_at.desc()
        )
        .all()
    )

    results = []

    for contract in contracts:
        opponent = (
            db.query(BoxingFighter)
            .filter(
                BoxingFighter.id
                == contract.opponent_id
            )
            .first()
        )

        event = (
            db.query(BoxingEvent)
            .filter(
                BoxingEvent.id
                == contract.event_id
            )
            .first()
        )

        bout = (
            db.query(BoxingBout)
            .filter(
                BoxingBout.id
                == contract.bout_id
            )
            .first()
        )

        results.append({
            "contract_id": contract.id,
            "bout_id": contract.bout_id,
            "status": (
                contract.status or "draft"
            ),
            "opponent": {
                "id": (
                    opponent.id
                    if opponent
                    else contract.opponent_id
                ),
                "name": (
                    opponent.legal_name
                    if opponent
                    else contract.opponent_name
                ),
                "record": (
                    opponent.pro_record
                    if opponent
                    else ""
                ),
                "gym": (
                    opponent.gym
                    if opponent
                    else ""
                ),
            },
            "event": {
                "id": contract.event_id,
                "name": (
                    contract.event_name
                    or (
                        event.name
                        if event
                        else ""
                    )
                ),
                "date": (
                    contract.event_date
                    or (
                        event.event_date
                        if event
                        else ""
                    )
                ),
                "venue": (
                    contract.venue
                    or (
                        event.venue
                        if event
                        else ""
                    )
                ),
                "venue_address": (
                    contract.venue_address
                    or (
                        event.venue_address
                        if event
                        else ""
                    )
                ),
            },
            "rounds": (
                contract.rounds
                or (
                    bout.rounds
                    if bout
                    else 4
                )
            ),
            "weight": (
                contract.maximum_weight
                if contract.maximum_weight is not None
                else (
                    bout.weight_agreed
                    if bout
                    else None
                )
            ),
            "purse": (
                contract.gross_purse or 0
            ),
            "travel_expense": (
                contract.travel_expense or 0
            ),
            "cancellation_pay": (
                contract.cancellation_pay or 0
            ),
            "additional_terms": (
                contract.additional_terms or ""
            ),
            "created_at": contract.created_at,
        })

    return {
        "fighter_id": account.fighter_id,
        "offers": results,
    }


@router.post("/me/fight-offers/{contract_id}/respond")
def fighter_respond_to_offer(
    contract_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = fighter_account_for_user(
        db,
        user,
    )

    action = str(
        data.get("action") or ""
    ).strip().lower()

    if action not in (
        "accept",
        "decline",
        "request_change",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Action must be accept, decline, "
                "or request_change"
            ),
        )

    contract = (
        db.query(BoxingContract)
        .filter(
            BoxingContract.id == contract_id,
            BoxingContract.fighter_id
            == account.fighter_id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Fight offer not found",
        )

    current_status = (
        contract.status or "draft"
    ).lower()

    if current_status in (
        "accepted",
        "declined",
        "signed",
        "completed",
        "cancelled",
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"This offer is already "
                f"{current_status}."
            ),
        )

    if action == "accept":
        contract.status = "accepted"
        response_message = "Fight offer accepted."

    elif action == "decline":
        contract.status = "declined"
        response_message = "Fight offer declined."

    else:
        request_note = str(
            data.get("message") or ""
        ).strip()

        if not request_note:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Please enter what you want "
                    "changed in the fight offer."
                ),
            )

        existing_terms = str(
            contract.additional_terms or ""
        ).strip()

        request_block = (
            "[FIGHTER CHANGE REQUEST]\n"
            + request_note
        )

        if existing_terms:
            contract.additional_terms = (
                existing_terms
                + "\n\n"
                + request_block
            )
        else:
            contract.additional_terms = (
                request_block
            )

        contract.status = "change_requested"
        response_message = (
            "Change request sent to TNG."
        )

    db.commit()
    db.refresh(contract)

    return {
        "ok": True,
        "contract_id": contract.id,
        "status": contract.status,
        "additional_terms":
            contract.additional_terms,
        "message": response_message,
    }


@router.get("/me/ticket-sales")
def fighter_ticket_sales(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = fighter_account_for_user(
        db,
        user,
    )

    fighter_id = account.fighter_id

    sellers = (
        db.query(EventSeller)
        .filter(
            EventSeller.seller_type == "fighter",
            EventSeller.seller_ref_id == fighter_id,
        )
        .order_by(EventSeller.created_at.desc())
        .all()
    )

    events = []
    total_tickets = 0
    total_gross_cents = 0
    total_commission_cents = 0
    total_paid_cents = 0

    for seller in sellers:
        event = (
            db.query(BoxingEvent)
            .filter(
                BoxingEvent.id == seller.event_id
            )
            .first()
        )

        tickets = (
            db.query(IssuedTicket)
            .filter(
                IssuedTicket.seller_id == seller.id,
                IssuedTicket.status != "refunded",
            )
            .all()
        )

        tickets_sold = len(tickets)

        gross_sales_cents = sum(
            int(ticket.price_cents or 0)
            for ticket in tickets
        )

        commission_cents = sum(
            int(ticket.commission_cents or 0)
            for ticket in tickets
        )

        payout = (
            db.query(SellerPayout)
            .filter(
                SellerPayout.event_id == seller.event_id,
                SellerPayout.seller_id == seller.id,
            )
            .order_by(
                SellerPayout.created_at.desc()
            )
            .first()
        )

        amount_paid_cents = (
            int(payout.amount_paid_cents or 0)
            if payout
            else 0
        )

        payout_status = (
            payout.status
            if payout
            else (
                "unpaid"
                if commission_cents > 0
                else "none"
            )
        )

        balance_due_cents = max(
            commission_cents
            - amount_paid_cents,
            0,
        )

        ticket_url = (
            "https://tngos.tngboxinggym.com"
            f"/events/{seller.event_id}/tickets"
            f"?seller={seller.public_code}"
        )

        qr_image = qrcode.make(ticket_url)
        qr_buffer = io.BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_png_base64 = base64.b64encode(
            qr_buffer.getvalue()
        ).decode()

        events.append({
            "event_id": seller.event_id,
            "event_name": (
                event.name
                if event
                else f"Event {seller.event_id}"
            ),
            "event_date": (
                event.event_date
                if event
                else None
            ),
            "venue": (
                event.venue
                if event
                else None
            ),
            "seller_id": seller.id,
            "seller_code": seller.public_code,
            "ticket_url": ticket_url,
            "qr_png_base64": qr_png_base64,
            "active": seller.active,
            "tickets_sold": tickets_sold,
            "gross_sales_cents": gross_sales_cents,
            "commission_cents": commission_cents,
            "amount_paid_cents": amount_paid_cents,
            "balance_due_cents": balance_due_cents,
            "payout_status": payout_status,
            "paid_at": (
                payout.paid_at
                if payout
                else None
            ),
        })

        total_tickets += tickets_sold
        total_gross_cents += gross_sales_cents
        total_commission_cents += commission_cents
        total_paid_cents += amount_paid_cents

    return {
        "fighter_id": fighter_id,
        "summary": {
            "tickets_sold": total_tickets,
            "gross_sales_cents": total_gross_cents,
            "commission_cents": total_commission_cents,
            "amount_paid_cents": total_paid_cents,
            "balance_due_cents": max(
                total_commission_cents
                - total_paid_cents,
                0,
            ),
        },
        "events": events,
    }



def _serialize_fighter_photo(photo):
    return {
        "id": photo.id,
        "fighter_id": photo.fighter_id,
        "file_name": photo.file_name,
        "content_type": photo.content_type,
        "file_size": photo.file_size,
        "photo_type": photo.photo_type,
        "is_primary": bool(photo.is_primary),
        "created_at": (
            photo.created_at.isoformat()
            if photo.created_at
            else None
        ),
        "image_url": (
            f"/api/fighter/me/photos/"
            f"{photo.id}/content"
        ),
    }


@router.get("/me/photos")
def fighter_list_photos(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    photos = (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.fighter_id
            == fighter.id
        )
        .order_by(
            FighterPhoto.is_primary.desc(),
            FighterPhoto.created_at.desc(),
        )
        .all()
    )

    return {
        "photos": [
            _serialize_fighter_photo(photo)
            for photo in photos
        ]
    }


@router.get("/me/photos/{photo_id}/content")
def fighter_photo_content(
    photo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    photo = (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.id == photo_id,
            FighterPhoto.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Photo not found.",
        )

    return Response(
        content=photo.file_data,
        media_type=photo.content_type,
        headers={
            "Cache-Control": "private, max-age=300"
        },
    )


@router.post("/me/photos")
async def fighter_upload_photo(
    file: UploadFile = File(...),
    photo_type: str = "headshot",
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    photo_type = str(
        photo_type or "headshot"
    ).strip().lower()

    allowed_types = {
        "headshot",
        "fight_pose",
        "action_shot",
    }

    if photo_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=(
                "Photo type must be headshot, "
                "fight_pose, or action_shot."
            ),
        )

    file_name = str(
        file.filename or "fighter-photo"
    ).strip()

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded photo is empty.",
        )

    max_size = 5 * 1024 * 1024

    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail=(
                "Fighter photo must be "
                "5 MB or smaller."
            ),
        )

    detected_type = None

    if contents.startswith(
        (b"\xff\xd8\xff",)
    ):
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
            detail=(
                "Photo must be a valid "
                "JPG, PNG, or WEBP image."
            ),
        )

    existing_count = (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.fighter_id
            == fighter.id
        )
        .count()
    )

    if existing_count >= 5:
        raise HTTPException(
            status_code=400,
            detail=(
                "Maximum of 5 fighter photos."
            ),
        )

    # First uploaded photo becomes primary automatically.
    is_primary = existing_count == 0

    photo = FighterPhoto(
        fighter_id=fighter.id,
        file_name=file_name,
        content_type=detected_type,
        file_size=len(contents),
        file_data=contents,
        photo_type=photo_type,
        is_primary=is_primary,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(photo)
    db.commit()
    db.refresh(photo)

    return {
        "ok": True,
        "message": (
            "Fighter photo uploaded successfully."
        ),
        "photo": _serialize_fighter_photo(photo),
    }


@router.post("/me/photos/{photo_id}/primary")
def fighter_set_primary_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    photo = (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.id == photo_id,
            FighterPhoto.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Photo not found.",
        )

    (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.fighter_id
            == fighter.id
        )
        .update(
            {
                FighterPhoto.is_primary:
                    False
            },
            synchronize_session=False,
        )
    )

    photo.is_primary = True
    photo.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(photo)

    return {
        "ok": True,
        "message": "Primary flyer photo updated.",
        "photo": _serialize_fighter_photo(photo),
    }


@router.delete("/me/photos/{photo_id}")
def fighter_delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account, fighter = _linked_fighter_account(
        user,
        db,
    )

    photo = (
        db.query(FighterPhoto)
        .filter(
            FighterPhoto.id == photo_id,
            FighterPhoto.fighter_id
            == fighter.id,
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Photo not found.",
        )

    was_primary = bool(photo.is_primary)

    db.delete(photo)
    db.commit()

    if was_primary:
        replacement = (
            db.query(FighterPhoto)
            .filter(
                FighterPhoto.fighter_id
                == fighter.id
            )
            .order_by(
                FighterPhoto.created_at.desc()
            )
            .first()
        )

        if replacement:
            replacement.is_primary = True
            replacement.updated_at = (
                datetime.utcnow()
            )
            db.commit()

    return {
        "ok": True,
        "message": "Fighter photo deleted.",
    }


@router.get("/me")
def fighter_me(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    account = fighter_account_for_user(
        db,
        user,
    )

    fighter = (
        db.query(BoxingFighter)
        .filter(
            BoxingFighter.id
            == account.fighter_id
        )
        .first()
    )

    if not fighter:
        raise HTTPException(
            status_code=404,
            detail=(
                "Fighter profile not found"
            ),
        )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "fighter": {
            "id": fighter.id,
            "legal_name": (
                fighter.legal_name
            ),
            "email": fighter.email,
            "phone": fighter.phone,
            "dob": fighter.dob,
            "city": fighter.city,
            "state": fighter.state,
            "country": fighter.country,
            "gym": fighter.gym,
            "coach": fighter.coach,
            "manager_name": (
                fighter.manager_name
            ),
            "manager_phone": (
                fighter.manager_phone
            ),
            "manager_email": (
                fighter.manager_email
            ),
            "pro_record": (
                fighter.pro_record
            ),
            "amateur_record": (
                fighter.amateur_record
            ),
            "boxrec_id": fighter.boxrec_id,
            "boxrec_url": (
                fighter.boxrec_url
            ),
            "fight_weight": (
                fighter.fight_weight
            ),
            "available_weight_min": (
                fighter.available_weight_min
            ),
            "available_weight_max": (
                fighter.available_weight_max
            ),
            "ok_license_status": (
                fighter.ok_license_status
            ),
            "federal_id_status": (
                fighter.federal_id_status
            ),
            "bloodwork_status": (
                fighter.bloodwork_status
            ),
            "bloodwork_expires": (
                fighter.bloodwork_expires
            ),
        },
    }

