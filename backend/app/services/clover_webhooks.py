"""Verify Clover Hosted Checkout signatures before processing payment events."""
import hashlib
import hmac
import os
import time

from fastapi import HTTPException


def verify_clover_webhook(body: bytes, signature: str) -> None:
    secret = os.getenv("CLOVER_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Payment webhook verification is not configured")
    try:
        parts = [part.strip().split("=", 1) for part in signature.split(",")]
        timestamps = [value for key, value in parts if key == "t"]
        signatures = [value for key, value in parts if key == "v1"]
        if len(timestamps) != 1 or not signatures:
            raise ValueError("Missing signature fields")
        timestamp = timestamps[0]
        if abs(time.time() - int(timestamp)) > 300:
            raise ValueError("Expired signature")
        expected = hmac.new(
            secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        if not any(hmac.compare_digest(expected, value) for value in signatures):
            raise ValueError("Invalid signature")
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid payment webhook signature")
