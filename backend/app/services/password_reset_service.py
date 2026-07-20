import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

import resend


RESET_TOKEN_EXPIRATION_SECONDS = 30 * 60
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://tngos.tngboxinggym.com",
).rstrip("/")


def _get_reset_secret() -> str:
    secret = os.getenv("PASSWORD_RESET_SECRET") or os.getenv("SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "PASSWORD_RESET_SECRET or SECRET_KEY must be configured."
        )

    return secret


def _base64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value: str) -> str:
    secret = _get_reset_secret().encode("utf-8")

    signature = hmac.new(
        secret,
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return _base64_encode(signature)


def create_password_reset_token(
    user_id: int,
    password_hash: str,
) -> str:
    payload = {
        "user_id": user_id,
        "issued_at": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
        "password_marker": hashlib.sha256(
            password_hash.encode("utf-8")
        ).hexdigest()[:24],
    }

    encoded_payload = _base64_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    signature = _sign(encoded_payload)

    return f"{encoded_payload}.{signature}"


def verify_password_reset_token(
    token: str,
    password_hash: str,
) -> dict[str, Any] | None:
    try:
        encoded_payload, supplied_signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(encoded_payload)

    if not hmac.compare_digest(
        supplied_signature,
        expected_signature,
    ):
        return None

    try:
        payload = json.loads(
            _base64_decode(encoded_payload).decode("utf-8")
        )
    except (ValueError, json.JSONDecodeError):
        return None

    issued_at = payload.get("issued_at")
    user_id = payload.get("user_id")
    password_marker = payload.get("password_marker")

    if not isinstance(issued_at, int):
        return None

    if not isinstance(user_id, int):
        return None

    if int(time.time()) - issued_at > RESET_TOKEN_EXPIRATION_SECONDS:
        return None

    current_marker = hashlib.sha256(
        password_hash.encode("utf-8")
    ).hexdigest()[:24]

    if not hmac.compare_digest(
        str(password_marker),
        current_marker,
    ):
        return None

    return payload


def send_password_reset_email(
    recipient_email: str,
    recipient_name: str,
    token: str,
) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv(
        "RESEND_FROM_EMAIL",
        "TNG Boxing <noreply@tngboxinggym.com>",
    )

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    resend.api_key = api_key

    reset_url = (
        f"{FRONTEND_URL}/reset-password"
        f"?token={token}"
    )

    safe_name = recipient_name.strip() or "TNG OS user"

    resend.Emails.send(
        {
            "from": from_email,
            "to": [recipient_email],
            "subject": "Reset your TNG OS password",
            "html": f"""
                <div style="
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: auto;
                    padding: 24px;
                    color: #18181b;
                ">
                    <h1 style="margin-bottom: 8px;">
                        Reset your TNG OS password
                    </h1>

                    <p>Hello {safe_name},</p>

                    <p>
                        We received a request to reset your TNG OS
                        password.
                    </p>

                    <p style="margin: 32px 0;">
                        <a
                            href="{reset_url}"
                            style="
                                background: #d71920;
                                color: white;
                                padding: 14px 22px;
                                border-radius: 8px;
                                text-decoration: none;
                                font-weight: bold;
                            "
                        >
                            Reset Password
                        </a>
                    </p>

                    <p>
                        This secure link expires in 30 minutes and
                        can only be used until your password changes.
                    </p>

                    <p>
                        If you did not request this reset, you can
                        safely ignore this email.
                    </p>

                    <hr style="
                        border: none;
                        border-top: 1px solid #e4e4e7;
                        margin: 28px 0;
                    ">

                    <p style="color: #71717a; font-size: 13px;">
                        TNG Boxing — Earned Not Given
                    </p>
                </div>
            """,
        }
    )