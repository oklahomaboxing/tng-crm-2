import os
from twilio.rest import Client


def send_sms(to_phone: str, message: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not twilio_number:
        raise RuntimeError("Twilio environment variables are missing.")

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=message,
        from_=twilio_number,
        to=to_phone
    )

    return message.sid