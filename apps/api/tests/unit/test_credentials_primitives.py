"""Tes primitif kredensial: password dan API token.

Yang diuji adalah sifat yang menentukan keamanan, bukan detail implementasi:
hash tidak mengandung password, verifikasi salah selalu False (tidak exception),
dan token yang dihasilkan tidak bisa ditebak dari prefix.
"""
from __future__ import annotations

from app.core.passwords import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    needs_rehash,
    password_policy_error,
    verify_password,
)
from app.core.tokens import generate_token, hash_token, looks_like_token, token_matches


def test_hash_does_not_contain_password():
    stored = hash_password("kalimat-rahasia-panjang")
    assert "kalimat-rahasia-panjang" not in stored
    assert stored.startswith("scrypt$")


def test_same_password_yields_different_hash():
    first = hash_password("kalimat-rahasia-panjang")
    second = hash_password("kalimat-rahasia-panjang")
    assert first != second  # salt acak per hash
    assert verify_password("kalimat-rahasia-panjang", first)
    assert verify_password("kalimat-rahasia-panjang", second)


def test_verify_rejects_wrong_password():
    stored = hash_password("kalimat-rahasia-panjang")
    assert verify_password("kalimat-rahasia-pendek", stored) is False


def test_verify_never_raises_on_malformed_hash():
    for bad in ("", None, "bukan-hash", "scrypt$rusak", "scrypt$x$y$z$@@@$@@@"):
        assert verify_password("apa-saja", bad) is False


def test_needs_rehash_detects_old_parameters():
    stored = hash_password("kalimat-rahasia-panjang")
    assert needs_rehash(stored) is False
    assert needs_rehash("scrypt$1024$8$1$c2FsdA==$aGFzaA==") is True
    assert needs_rehash("bukan-hash") is True


def test_password_policy_requires_length():
    assert password_policy_error("pendek") is not None
    assert password_policy_error("x" * MIN_PASSWORD_LENGTH) is None
    assert password_policy_error(" " * MIN_PASSWORD_LENGTH) is not None


def test_token_format_and_hash():
    plaintext, prefix, digest = generate_token()
    assert plaintext.startswith(prefix + "_")
    assert looks_like_token(plaintext)
    assert digest == hash_token(plaintext)
    assert digest != plaintext
    assert token_matches(plaintext, digest)


def test_token_rejects_tampered_secret():
    plaintext, _, digest = generate_token()
    tampered = plaintext[:-1] + ("a" if plaintext[-1] != "a" else "b")
    assert token_matches(tampered, digest) is False


def test_looks_like_token_rejects_other_bearer_values():
    assert looks_like_token("") is False
    assert looks_like_token("ops-dev-token") is False
    assert looks_like_token("eyJhbGciOiJIUzI1NiJ9.payload.sig") is False
    assert looks_like_token("dx_abc_secret") is False  # prefix terlalu pendek


def test_looks_like_token_accepts_underscores_in_secret():
    """Regresi: alphabet base64url memuat `_`, jadi secret sah bisa mengandungnya."""
    secret = "a" * 20 + "_b_c_d"
    assert looks_like_token(f"dx_0123456789ab_{secret}") is True


def test_generated_tokens_always_parse():
    """100 token acak: bentuknya harus selalu diterima, tanpa kecuali."""
    for _ in range(100):
        plaintext, _, _ = generate_token()
        assert looks_like_token(plaintext), plaintext


def test_tokens_are_unique():
    seen = {generate_token()[0] for _ in range(50)}
    assert len(seen) == 50
