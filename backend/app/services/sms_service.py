import os
import re
from twilio.rest import Client


STOP_FOOTER = "Reply STOP to unsubscribe."


def ensure_stop_footer(message: str) -> str:
    """Use one consistent opt-out line on every application-generated SMS."""
    text = re.sub(r"\s*(?:reply|text)\s+stop\s+to\s+(?:opt[ -]out|unsubscribe|stop receiving messages)[.!]?", "", str(message or "").strip(), flags=re.IGNORECASE).strip()
    return f"{text} {STOP_FOOTER}".strip()


def send_sms(to_phone: str, message: str, status_callback: str | None = None):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not twilio_number:
        raise RuntimeError("Twilio environment variables are missing.")

    client = Client(account_sid, auth_token)

    options = {"status_callback": status_callback} if status_callback else {}
    message = client.messages.create(
        body=ensure_stop_footer(message),
        from_=twilio_number,
        to=to_phone,
        **options,
    )

    return message.sid
