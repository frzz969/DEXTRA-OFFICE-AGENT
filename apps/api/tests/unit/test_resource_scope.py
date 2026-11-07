"""Tests for resource-scope enforcement helper (A-03 fondasi)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.resource_scope import resource_allowed


@dataclass
class FakeCaller:
    scope: str = "ops"
    principal_id: str | None = None


def test_no_owner_allows():
    assert resource_allowed(FakeCaller(), None) is True
    assert resource_allowed(FakeCaller(), "") is True


def test_owner_match_allows():
    c = FakeCaller(principal_id="usr_nadia")
    assert resource_allowed(c, "usr_nadia") is True


def test_owner_mismatch_denies():
    c = FakeCaller(principal_id="usr_nadia")
    assert resource_allowed(c, "usr_sari") is False


def test_legacy_token_denied_on_owned_resource():
    # Token tanpa principal tidak boleh menyentuh resource berpemilik.
    c = FakeCaller(principal_id=None)
    assert resource_allowed(c, "usr_nadia") is False


def test_legacy_token_allowed_on_unowned_resource():
    c = FakeCaller(principal_id=None)
    assert resource_allowed(c, None) is True
