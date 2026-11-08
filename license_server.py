"""Minimal Stripe webhook that emails signed lifetime PRO licenses.

Required environment variables are documented in LICENSE_SETUP.md.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import smtplib
import sqlite3
import sys
import time
import uuid
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DB_PATH = Path(os.environ.get("MEDIA_FLOW_LICENSE_DB", "licenses.sqlite3"))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def issue_license(purchase_id: str, email: str) -> str:
    private_raw = base64.b64decode(os.environ["MEDIA_FLOW_LICENSE_PRIVATE_KEY"])
    private_key = Ed25519PrivateKey.from_private_bytes(private_raw)
    payload = json.dumps(
        {"product": "mediaflow-pro", "purchase": purchase_id, "email": email,
         "issued": int(time.time()), "nonce": uuid.uuid4().hex},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return f"MFPRO1.{b64url(payload)}.{b64url(private_key.sign(payload))}"


def send_license(email: str, key: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Tu licencia de Media Flow PRO"
    message["From"] = os.environ["MEDIA_FLOW_EMAIL_FROM"]
    message["To"] = email
    message.set_content(
        "Gracias por comprar Media Flow PRO.\n\n"
        "Abre Media Flow > Complemento PRO, pega esta licencia y pulsa Activar:\n\n"
        f"{key}\n\nGuarda este correo para futuras instalaciones."
    )
    host = os.environ["MEDIA_FLOW_SMTP_HOST"]
    port = int(os.environ.get("MEDIA_FLOW_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(os.environ["MEDIA_FLOW_SMTP_USER"], os.environ["MEDIA_FLOW_SMTP_PASSWORD"])
        smtp.send_message(message)


def verify_stripe_signature(raw: bytes, header: str, secret: str) -> bool:
    fields = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
    timestamp = fields.get("t", "")
    signatures = [item.split("=", 1)[1] for item in header.split(",") if item.startswith("v1=")]
    try:
        if abs(int(time.time()) - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    signed = timestamp.encode() + b"." + raw
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)


def fulfill(event: dict) -> None:
    session = event["data"]["object"]
    if session.get("mode") != "payment" or session.get("payment_status") != "paid":
        # Delayed payment methods may send completed before payment settles.
        # Their later async_payment_succeeded event triggers fulfillment.
        return
    expected_link = os.environ["STRIPE_PAYMENT_LINK_ID"]
    if session.get("payment_link") != expected_link:
        raise ValueError("Payment Link does not match the configured PRO product")
    email = (session.get("customer_details") or {}).get("email") or session.get("customer_email")
    purchase_id = session.get("id")
    if not email or not purchase_id:
        raise ValueError("Paid session is missing its customer email or ID")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS deliveries (purchase_id TEXT PRIMARY KEY, email TEXT NOT NULL, license TEXT NOT NULL)")
        row = db.execute("SELECT 1 FROM deliveries WHERE purchase_id=?", (purchase_id,)).fetchone()
        if row:
            return
        key = issue_license(purchase_id, email)
        send_license(email, key)
        db.execute("INSERT INTO deliveries VALUES (?, ?, ?)", (purchase_id, email, key))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()
        if self.path == "/health":
            self.wfile.write(b"ok")

    def do_POST(self) -> None:
        if self.path != "/stripe/webhook":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length < 1 or content_length > 1_000_000:
            self.send_error(413, "Invalid webhook payload size")
            return
        raw = self.rfile.read(content_length)
        if not verify_stripe_signature(raw, self.headers.get("Stripe-Signature", ""), os.environ["STRIPE_WEBHOOK_SECRET"]):
            self.send_error(400, "Invalid Stripe signature")
            return
        try:
            event = json.loads(raw)
            if event.get("type") in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
                fulfill(event)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception as exc:
            # A 500 makes Stripe retry if email delivery or configuration failed.
            print(f"Webhook fulfillment failed: {exc}", file=sys.stderr, flush=True)
            self.send_error(500, "License delivery failed")


def generate_keys() -> None:
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    print("MEDIA_FLOW_LICENSE_PRIVATE_KEY=" + base64.b64encode(private).decode())
    print("MEDIA_FLOW_LICENSE_PUBLIC_KEY=" + base64.b64encode(public).decode())
    print("Keep the PRIVATE key only in the webhook host's secret manager.", file=sys.stderr)


if __name__ == "__main__":
    if "--generate-keys" in sys.argv:
        generate_keys()
    else:
        ThreadingHTTPServer((os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
