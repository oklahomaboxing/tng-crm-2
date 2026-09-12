import hashlib
import os
import secrets
from datetime import datetime, timedelta

import resend
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..auth import decode_token, hash_password
from ..database import Base, engine, get_db
from ..models import User
from ..matchmaker.models import BoxingFighter, BoxingEvent
from ..ticketing.models import EventSeller, IssuedTicket, SellerPayout
from .models import FighterAccount, FighterInvite
from .schemas import ActivateFighterIn, InviteFighterIn


Base.metadata.create_all(bind=engine)

router = APIRouter(
    prefix="/api/fighter",
    tags=["Fighter Portal"],
)


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

