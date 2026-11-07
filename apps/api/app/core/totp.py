"""TOTP (RFC 6238) dengan standard library.

Tidak memakai `pyotp`: algoritmanya pendek, dan menambah dependency untuk 40
baris kode berarti menambah permukaan pasokan tanpa manfaat. Yang dipakai hanya
`hmac`, `hashlib`, `base64`, `struct`.

Parameter: SHA-1, 30 detik, 6 digit — kombinasi yang diterima Google
Authenticator, Authy, dan 1Password. Jendela verifikasi ±1 langkah untuk
mengakomodasi selisih jam, dan **kode yang sudah dipakai tidak bisa dipakai
lagi** (lihat `verify_code` dengan `last_used_step`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse

STEP_SECONDS = 30
DIGITS = 6
#: Toleransi satu langkah ke belakang dan satu ke depan (±30 detik).
DEFAULT_WINDOW = 1


def generate_secret() -> str:
    """Secret base32 160-bit, tanpa padding (format yang diterima authenticator)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padded = secret.strip().upper()
    padding = (-len(padded)) % 8
    return base64.b32decode(padded + "=" * padding, casefold=True)


def code_at(secret: str, timestamp: float, *, step: int = STEP_SECONDS, digits: int = DIGITS) -> str:
    counter = int(timestamp // step)
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10**digits)).zfill(digits)


def current_step(timestamp: float | None = None, *, step: int = STEP_SECONDS) -> int:
    return int((timestamp if timestamp is not None else time.time()) // step)


def verify_code(
    secret: str,
    code: str,
    *,
    timestamp: float | None = None,
    window: int = DEFAULT_WINDOW,
    last_used_step: int | None = None,
) -> tuple[bool, int | None]:
    """Kembalikan (sah, langkah_waktu_yang_dipakai).

    `last_used_step` mencegah pemakaian ulang kode yang sama dalam jendela yang
    sama. Tanpa ini, kode yang sudah dicegat masih berlaku sampai 30 detik
    berikutnya.
    """
    if not secret or not code:
        return False, None
    cleaned = code.strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != DIGITS:
        return False, None

    moment = timestamp if timestamp is not None else time.time()
    base = current_step(moment)
    for offset in range(-window, window + 1):
        candidate_step = base + offset
        if last_used_step is not None and candidate_step <= last_used_step:
            continue
        expected = code_at(secret, candidate_step * STEP_SECONDS)
        if hmac.compare_digest(expected, cleaned):
            return True, candidate_step
    return False, None


def provisioning_uri(secret: str, *, account: str, issuer: str) -> str:
    """URI `otpauth://` untuk ditampilkan sebagai QR atau diketik manual."""
    label = urllib.parse.quote(f"{issuer}:{account}", safe="")
    params = urllib.parse.urlencode(
        {
            "secret": secret,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": DIGITS,
            "period": STEP_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{params}"
