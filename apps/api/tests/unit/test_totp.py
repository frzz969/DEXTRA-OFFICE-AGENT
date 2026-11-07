"""TOTP terhadap vektor uji RFC 6238.

Menguji implementasi sendiri dengan vektor resmi lebih berarti daripada
mengujinya dengan implementasi sendiri juga: vektor ini berasal dari spesifikasi,
bukan dari kode ini.
"""
from __future__ import annotations

import base64

import pytest

from app.core import totp

#: Secret uji dari RFC 6238 Lampiran B ("12345678901234567890").
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode("ascii").rstrip("=")

RFC_VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


@pytest.mark.parametrize("timestamp,expected", RFC_VECTORS)
def test_matches_rfc6238_vectors(timestamp, expected):
    assert totp.code_at(RFC_SECRET, timestamp, digits=8) == expected


def test_six_digit_default():
    assert len(totp.code_at(RFC_SECRET, 59)) == 6
    assert totp.code_at(RFC_SECRET, 59) == "287082"  # 6 digit terakhir vektor RFC


def test_verify_accepts_current_window():
    secret = totp.generate_secret()
    code = totp.code_at(secret, 1_700_000_000)
    ok, step = totp.verify_code(secret, code, timestamp=1_700_000_000)
    assert ok and step == totp.current_step(1_700_000_000)


def test_verify_tolerates_one_step_drift():
    secret = totp.generate_secret()
    code = totp.code_at(secret, 1_700_000_000 - 30)
    ok, _ = totp.verify_code(secret, code, timestamp=1_700_000_000)
    assert ok


def test_verify_rejects_outside_window():
    secret = totp.generate_secret()
    code = totp.code_at(secret, 1_700_000_000 - 300)
    ok, _ = totp.verify_code(secret, code, timestamp=1_700_000_000)
    assert not ok


def test_verify_rejects_malformed_code():
    secret = totp.generate_secret()
    for bad in ("", "abcdef", "12345", "1234567"):
        ok, _ = totp.verify_code(secret, bad, timestamp=1_700_000_000)
        assert not ok


def test_verify_rejects_replayed_step():
    secret = totp.generate_secret()
    moment = 1_700_000_000
    code = totp.code_at(secret, moment)
    ok, step = totp.verify_code(secret, code, timestamp=moment)
    assert ok
    again, _ = totp.verify_code(secret, code, timestamp=moment, last_used_step=step)
    assert not again


def test_provisioning_uri_is_well_formed():
    uri = totp.provisioning_uri("ABC234", account="a@b.test", issuer="DEXTRA")
    assert uri.startswith("otpauth://totp/")
    assert "secret=ABC234" in uri
    assert "issuer=DEXTRA" in uri
