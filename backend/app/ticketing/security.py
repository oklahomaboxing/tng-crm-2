import hashlib, hmac, os, secrets
from urllib.parse import quote
from cryptography.fernet import Fernet, InvalidToken

QR_SECRET = os.getenv("TICKET_QR_SECRET", "")

def require_secret():
    if not QR_SECRET or len(QR_SECRET) < 32:
        raise RuntimeError("TICKET_QR_SECRET must be set to a random value of at least 32 characters")

def make_raw_token(event_id: int, ticket_number: str) -> str:
    require_secret()
    nonce = secrets.token_urlsafe(18)
    payload = f"{event_id}:{ticket_number}:{nonce}"
    sig = hmac.new(QR_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()

def verify_token(raw_token: str) -> bool:
    require_secret()
    try:
        event_id, ticket_number, nonce, sig = raw_token.split(":", 3)
        payload = f"{event_id}:{ticket_number}:{nonce}"
        expected = hmac.new(QR_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False

def _fernet():
    require_secret()
    key = hashlib.sha256(QR_SECRET.encode()).digest()
    import base64
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(raw_token: str) -> str:
    return _fernet().encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        raise ValueError("Invalid encrypted QR token")