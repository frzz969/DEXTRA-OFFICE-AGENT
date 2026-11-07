"""Enkripsi kolom mfa_secret at-rest (A14).

Tanpa dependensi baru: scrypt(DEXTRA_MFA_KEY) -> kunci 32-byte, lalu
HMAC-based stream cipher (hashlib/hmac) dengan nonce acak per nilai.
Format: enc$v1$<nonce_b64>$<ct_b64>  (kunci scrypt pakai salt tetap, bukan per-nilai)

Aturan jujur:
- Dev/test tanpa DEXTRA_MFA_KEY: encryption DISABLED, secret disimpan apa
  adanya (back-compat, TANPA klaim enkripsi). Peringatan dicatat sekali.
- Production (DEXTRA_ENV=production): kunci WAJIB ada, jangan startup diam-diam
  dengan plaintext.
- Nilai lama (tanpa prefix enc$) otomatis dibaca sebagai plaintext supaya
  migrasi tidak memutus user yang sudah enroll; ditulis ulang terenkripsi
  pada enrollment/rotasi berikutnya.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

_PREFIX = "enc$v1$"
_warned = False


def _key() -> bytes | None:
    raw = (os.environ.get("DEXTRA_MFA_KEY") or "").strip()
    if not raw:
        return None
    salt = b"dextra-mfa-column-v1"
    return hashlib.scrypt(raw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32, maxmem=132*2**14*8)


def _warn_once() -> None:
    global _warned
    if _warned:
        return
    _warned = True
    import logging
    logging.getLogger(__name__).warning(
        "DEXTRA_MFA_KEY tidak diset: mfa_secret disimpan PLAINTEXT (dev/test saja). "
        "Di production set DEXTRA_MFA_KEY sebelum start."
    )


def _stream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = b""
    i = 0
    while len(out) < length:
        out += hmac.new(key, nonce + i.to_bytes(4, "big"), hashlib.sha256).digest()
        i += 1
    return out[:length]


def encrypt_secret(secret: str) -> str:
    """Enkripsi bila kunci ada; bila tidak, kembalikan plaintext (dev)."""
    if not secret:
        raise ValueError("secret kosong")
    key = _key()
    if key is None:
        env = (os.environ.get("DEXTRA_ENV") or "development").strip().lower()
        if env == "production":
            raise RuntimeError("DEXTRA_MFA_KEY wajib diset di production mode")
        _warn_once()
        return secret
    nonce = secrets.token_bytes(16)
    pt = secret.encode()
    ct = bytes(a ^ b for a, b in zip(pt, _stream(key, nonce, len(pt))))
    return _PREFIX + base64.b64encode(nonce).decode() + "$" + base64.b64encode(ct).decode()


def decrypt_secret(stored: str | None) -> str | None:
    if not stored:
        return None
    if not stored.startswith(_PREFIX):
        return stored  # legacy plaintext
    key = _key()
    if key is None:
        raise RuntimeError("mfa_secret terenkripsi tetapi DEXTRA_MFA_KEY tidak diset")
    _, _, nonce_b64, ct_b64 = stored.split("$", 3)
    nonce = base64.b64decode(nonce_b64.encode())
    ct = base64.b64decode(ct_b64.encode())
    pt = bytes(a ^ b for a, b in zip(ct, _stream(key, nonce, len(ct))))
    return pt.decode()


def is_encrypted(stored: str | None) -> bool:
    return bool(stored and stored.startswith(_PREFIX))
