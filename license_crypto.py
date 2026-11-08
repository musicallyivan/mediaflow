"""Offline verification for signed Media Flow PRO licenses."""

import base64
import json
import os
import sys
from pathlib import Path

# Set this before building the Windows app to the public key printed by
# license_server.py --generate-keys. The matching private key stays server-side.
def _public_key_b64() -> str:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    try:
        return (root / "license_public_key.txt").read_text(encoding="ascii").strip()
    except OSError:
        return ""


def verify_license_key(key: str) -> bool:
    parts = key.strip().split(".")
    public_key_b64 = _public_key_b64()
    if len(parts) != 3 or parts[0] != "MFPRO1" or not public_key_b64:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        payload = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        signature = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
        public_key = base64.b64decode(public_key_b64)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
        data = json.loads(payload)
        return data.get("product") == "mediaflow-pro" and bool(data.get("purchase"))
    except Exception:
        return False
