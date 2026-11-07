"""Pembuatan dan hashing API token.

Token dibuat acak 256-bit. Karena entropinya tinggi, SHA-256 cukup untuk
penyimpanan — berbeda dengan password yang butuh fungsi lambat. Yang penting:
secret mentah tidak pernah disimpan, dan perbandingan dilakukan dengan
`compare_digest`.

Format token:

    dx_<12 hex prefix>_<43 char secret>

Prefix bukan rahasia; ia hanya untuk menampilkan token mana yang dipakai di
inventaris tanpa membuka secret-nya.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

PREFIX_BYTES = 6  # -> 12 karakter hex
SECRET_BYTES = 32  # -> 43 karakter base64url tanpa padding


def hash_token(plaintext: str) -> str:
    """Hash yang disimpan di kolom `api_tokens.token_hash`."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def generate_token() -> tuple[str, str, str]:
    """Kembalikan (plaintext, prefix, hash).

    Plaintext hanya boleh muncul di respons pembuatan token. Setelah itu tidak
    ada cara mengambilnya kembali — hanya hash yang tersimpan.
    """
    prefix = f"dx_{secrets.token_hex(PREFIX_BYTES)}"
    secret = secrets.token_urlsafe(SECRET_BYTES)
    plaintext = f"{prefix}_{secret}"
    return plaintext, prefix, hash_token(plaintext)


def token_matches(plaintext: str, stored_hash: str) -> bool:
    if not plaintext or not stored_hash:
        return False
    return hmac.compare_digest(hash_token(plaintext), stored_hash)


def looks_like_token(value: str | None) -> bool:
    """Cek bentuk kasar sebelum query database.

    Bukan pengaman — hanya menghindari query untuk nilai yang jelas bukan token
    (mis. bearer yang kosong atau JWT dari sistem lain).

    `split("_", 2)` dan bukan `split("_")`: alphabet base64url memuat `_`, jadi
    secret bisa mengandung garis bawah. Memecah seluruh string akan menolak
    token yang sah secara acak — bug yang hanya muncul pada sebagian token.
    """
    if not value or not value.startswith("dx_"):
        return False
    parts = value.split("_", 2)
    return len(parts) == 3 and len(parts[1]) == PREFIX_BYTES * 2 and len(parts[2]) >= 20
