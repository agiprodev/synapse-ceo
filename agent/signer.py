import hashlib
import hmac
import json

SHARED_SECRET = "beast_mode_secret_key_2026"


def sign_action(payload: dict) -> str:
    payload_str = json.dumps(payload, sort_keys=True)
    return hmac.new(
        SHARED_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_action(payload: dict, signature: str) -> bool:
    expected_sig = sign_action(payload)
    return hmac.compare_digest(expected_sig, signature)
