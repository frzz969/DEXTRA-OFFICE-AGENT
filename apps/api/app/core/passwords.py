"""Hash password dengan scrypt dari standard library.

Tidak ada dependency baru: `hashlib.scrypt` tersedia di Python 3.11+ dan
memenuhi kebutuhan (memory-hard, salt per pengguna, parameter tersimpan di
dalam hash sehingga bisa dinaikkan tanpa migrasi kolom).

Format yang disimpan:

    scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>

Parameter ikut disimpan supaya verifikasi tetap bisa dilakukan setelah parameter
default dinaikkan, dan `needs_rehash` bisa memberi tahu kapan hash lama layak
diperbarui.

Yang tidak dilakukan di sini: mengarang password. `hash_password` tidak punya
nilai default, dan pemanggil harus menyediakan password yang benar-benar dipilih
pengguna atau diacak secara eksplisit.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ALGORITHM = "scrypt"
_N = 2**15  # 32768 (A14 naik; format simpan N sehingga hash lama tetap verifikasi)
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16

#: Batas bawah panjang password. Bukan aturan kerumitan — panjang lebih berguna
#: daripada campuran karakter, dan aturan kerumitan mendorong pola yang mudah
#: ditebak.
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=dklen,
        maxmem=132 * n * r,
    )


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password tidak boleh kosong.")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _derive(password, salt, _N, _R, _P, _DKLEN)
    return f"{_ALGORITHM}${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    """Verifikasi tanpa membocorkan apakah hash ada atau formatnya rusak.

    Hash kosong/rusak diperlakukan sebagai "tidak cocok", bukan exception:
    penyerang tidak boleh bisa membedakan "pengguna tidak punya password" dari
    "password salah" lewat kode status atau stack trace.
    """
    if not password or not stored:
        return False
    try:
        algorithm, n_raw, r_raw, p_raw, salt_raw, digest_raw = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        salt = _unb64(salt_raw)
        expected = _unb64(digest_raw)
    except (ValueError, TypeError):
        return False
    try:
        actual = _derive(password, salt, n, r, p, len(expected))
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str | None) -> bool:
    """True bila hash memakai parameter di bawah default saat ini."""
    if not stored:
        return False
    try:
        algorithm, n_raw, r_raw, p_raw, _, _ = stored.split("$")
    except ValueError:
        return True
    if algorithm != _ALGORITHM:
        return True
    return (int(n_raw), int(r_raw), int(p_raw)) != (_N, _R, _P)


def password_policy_error(password: str) -> str | None:
    """Pesan kesalahan bila password tidak memenuhi syarat, selain itu None."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        return f"Password minimal {MIN_PASSWORD_LENGTH} karakter."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password maksimal {MAX_PASSWORD_LENGTH} karakter."
    if password.strip() == "":
        return "Password tidak boleh hanya berisi spasi."
    return None
