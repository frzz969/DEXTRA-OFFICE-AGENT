"""Policy engine deterministik: masukan sama, keputusan sama, tanpa model."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.governance import policy  # noqa: E402


def test_clean_plan_is_allowed():
    result = policy.evaluate(policy.PlanInput(action_type="send_email", at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc)))
    assert result.decision == policy.ALLOW
    assert result.reason_code == ""


def test_recipient_outside_scope_is_denied():
    result = policy.evaluate(
        policy.PlanInput(
            action_type="send_email",
            recipients=("vendor@luar.example",),
            allowed_recipients=("internal@example.com",),
            at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        )
    )
    assert result.decision == policy.DENY
    assert result.reason_code == policy.RECIPIENT_NOT_ALLOWED


def test_ambiguous_recipient_requires_review():
    result = policy.evaluate(
        policy.PlanInput(
            action_type="send_email",
            recipient_candidates=3,
            at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        )
    )
    assert result.decision == policy.REVIEW
    assert result.reason_code == policy.AMBIGUOUS_RECIPIENT


def test_injection_is_denied_even_if_everything_else_clean():
    result = policy.evaluate(
        policy.PlanInput(
            action_type="send_email",
            contains_injection=True,
            at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        )
    )
    assert result.decision == policy.DENY
    assert result.reason_code == policy.INJECTION_QUARANTINED


def test_deny_beats_review():
    result = policy.evaluate(
        policy.PlanInput(
            action_type="send_email",
            recipients=("vendor@luar.example",),
            allowed_recipients=("internal@example.com",),
            recipient_candidates=2,
            at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        )
    )
    assert result.decision == policy.DENY
    codes = {f.code for f in result.findings}
    assert policy.AMBIGUOUS_RECIPIENT in codes


def test_outside_office_hours_requires_review():
    result = policy.evaluate(
        policy.PlanInput(action_type="send_email", at=datetime(2026, 11, 3, 22, tzinfo=timezone.utc))
    )
    assert result.decision == policy.REVIEW
    assert result.reason_code == policy.OUTSIDE_OFFICE_HOURS


def test_bulk_egress_requires_review():
    result = policy.evaluate(
        policy.PlanInput(
            action_type="send_email",
            recipient_count=50,
            at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
        )
    )
    assert result.decision == policy.REVIEW
    assert result.reason_code == policy.BULK_EGRESS_SUSPECTED


def test_evaluation_is_deterministic():
    plan = policy.PlanInput(
        action_type="send_email",
        recipients=("vendor@luar.example",),
        allowed_recipients=("internal@example.com",),
        at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
    )
    first = policy.evaluate(plan)
    for _ in range(5):
        assert policy.evaluate(plan) == first
