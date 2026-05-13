# -*- coding: utf-8 -*-
"""AES-256-GCM encryption for hot-wallet passphrase.

The master key lives ONLY in the server environment variable
PRIZM_MASTER_KEY (32 random bytes, base64url-encoded, no padding).
The ciphertext is stored in the DB table app_config under the key
'hot_wallet_passphrase_enc'.

Blob format: base64url( nonce[12] || aesgcm_ciphertext_with_tag )
The cryptography library appends the 16-byte authentication tag at the
end of the ciphertext automatically.

Quick setup:
    python -c "from backend.utils.wallet_crypto import generate_master_key; print(generate_master_key())"
Then put the output into .env as PRIZM_MASTER_KEY=<value>.
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _master_key() -> bytes:
    raw = os.getenv("PRIZM_MASTER_KEY", "").strip().rstrip("=")
    if not raw:
        raise RuntimeError(
            "PRIZM_MASTER_KEY is not set. "
            "Generate one with: python -c \"from backend.utils.wallet_crypto import generate_master_key; print(generate_master_key())\""
        )
    try:
        # Add back padding so b64decode is happy
        key = base64.urlsafe_b64decode(raw + "==")
    except Exception as exc:
        raise RuntimeError(f"PRIZM_MASTER_KEY is not valid base64url: {exc}") from exc
    if len(key) != 32:
        raise RuntimeError(
            f"PRIZM_MASTER_KEY must decode to exactly 32 bytes for AES-256 (got {len(key)} bytes). "
            "Regenerate it with generate_master_key()."
        )
    return key


def encrypt_passphrase(plaintext: str) -> str:
    """Encrypt a passphrase string.

    Returns a base64url-encoded blob: nonce(12) + aesgcm_output(len+16).
    Safe to store in plain text in the database.
    """
    key = _master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = nonce + ct_with_tag
    return base64.urlsafe_b64encode(blob).rstrip(b"=").decode("ascii")


def decrypt_passphrase(blob: str) -> str:
    """Decrypt a passphrase from the base64url-encoded blob.

    Raises ValueError if the blob is tampered or the key is wrong.
    """
    key = _master_key()
    aesgcm = AESGCM(key)
    raw = base64.urlsafe_b64decode(blob.rstrip("=") + "==")
    if len(raw) < 28:  # 12-byte nonce + 16-byte tag minimum
        raise ValueError("Encrypted passphrase blob is too short or corrupted.")
    nonce = raw[:12]
    ct_with_tag = raw[12:]
    plaintext = aesgcm.decrypt(nonce, ct_with_tag, None)
    return plaintext.decode("utf-8")


def generate_master_key() -> str:
    """Generate a new random 256-bit master key encoded as base64url (no padding).

    Run once during initial server setup and store the output in .env as PRIZM_MASTER_KEY.
    Keep this key secret — losing it means the stored passphrase cannot be decrypted.
    """
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
