"""Policy engine deterministik.

Policy Validator **bukan** agen AI (§8.3). Fungsi-fungsi di sini murni: masukan
sama selalu menghasilkan keputusan yang sama, tanpa panggilan model, tanpa
jaringan, tanpa waktu implisit (waktu selalu diberikan sebagai argumen).

Reason code sengaja sama dengan packages/policy-engine/src/rules.ts supaya dua
implementasi tidak bercerita berbeda tentang penolakan yang sama.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

ALLOW = "allow"
DENY = "deny"
REVIEW = "review"

#: Reason code yang dipakai bersama dengan implementasi TypeScript.
RECIPIENT_NOT_ALLOWED = "RECIPIENT_NOT_ALLOWED"
AMBIGUOUS_RECIPIENT = "AMBIGUOUS_RECIPIENT"
OUTSIDE_OFFICE_HOURS = "OUTSIDE_OFFICE_HOURS"
HOLIDAY_CONFLICT = "HOLIDAY_CONFLICT"
FRIDAY_PRAYER_CONFLICT = "FRIDAY_PRAYER_CONFLICT"
BULK_EGRESS_SUSPECTED = "BULK_EGRESS_SUSPECTED"
INJECTION_QUARANTINED = "INJECTION_QUARANTINED"
UNKNOWN_TIMEZONE = "UNKNOWN_TIMEZONE"


@dataclass(frozen=True)
class PolicyRule:
    code: str
    decision: str
    message: str


@dataclass(frozen=True)
class PlanInput:
    action_type: str
    recipients: tuple[str, ...] = ()
    allowed_recipients: tuple[str, ...] = ()
    recipient_candidates: int = 1
    at: datetime | None = None
    office_hours: tuple[int, int] = (8, 18)
    is_holiday: bool = False
    is_friday_prayer: bool = False
    recipient_count: int = 1
    bulk_threshold: int = 25
    contains_injection: bool = False


@dataclass(frozen=True)
class Evaluation:
    decision: str
    reason_code: str = ""
    detail: str = ""
    findings: tuple[PolicyRule, ...] = field(default_factory=tuple)


def evaluate(plan: PlanInput) -> Evaluation:
    """Evaluasi deterministik. Penolakan mengalahkan permintaan review."""
    findings: list[PolicyRule] = []

    if plan.contains_injection:
        findings.append(
            PolicyRule(INJECTION_QUARANTINED, DENY, "Instruksi tersisip di dalam konten.")
        )

    if plan.recipient_candidates > 1:
        findings.append(
            PolicyRule(
                AMBIGUOUS_RECIPIENT,
                REVIEW,
                f"{plan.recipient_candidates} kandidat penerima; perlu dipilih manusia.",
            )
        )

    if plan.allowed_recipients:
        unknown = [r for r in plan.recipients if r not in plan.allowed_recipients]
        if unknown:
            findings.append(
                PolicyRule(
                    RECIPIENT_NOT_ALLOWED,
                    DENY,
                    "Penerima di luar scope: " + ", ".join(sorted(unknown)),
                )
            )

    if plan.recipient_count > plan.bulk_threshold:
        findings.append(
            PolicyRule(
                BULK_EGRESS_SUSPECTED,
                REVIEW,
                f"{plan.recipient_count} penerima melebihi ambang {plan.bulk_threshold}.",
            )
        )

    if plan.is_holiday:
        findings.append(PolicyRule(HOLIDAY_CONFLICT, REVIEW, "Jatuh pada hari libur."))

    if plan.is_friday_prayer:
        findings.append(PolicyRule(FRIDAY_PRAYER_CONFLICT, REVIEW, "Bertabrakan dengan salat Jumat."))

    if plan.at is not None:
        start, end = plan.office_hours
        if not (start <= plan.at.hour < end):
            findings.append(
                PolicyRule(
                    OUTSIDE_OFFICE_HOURS,
                    REVIEW,
                    f"Di luar jam kerja {start:02d}:00-{end:02d}:00.",
                )
            )

    if any(f.decision == DENY for f in findings):
        first = next(f for f in findings if f.decision == DENY)
        return Evaluation(decision=DENY, reason_code=first.code, detail=first.message, findings=tuple(findings))

    if any(f.decision == REVIEW for f in findings):
        first = next(f for f in findings if f.decision == REVIEW)
        return Evaluation(
            decision=REVIEW, reason_code=first.code, detail=first.message, findings=tuple(findings)
        )

    return Evaluation(decision=ALLOW, findings=tuple(findings))
