"""Worker pemeliharaan DEXTRA.

Eksekusi saat ini sinkron, jadi worker ini bukan mesin antrean. Tugasnya dua hal
yang memang dibutuhkan dan bisa diverifikasi:

1. Menandai mandate yang sudah lewat masa berlaku sebagai `expired`.
   Tanpa ini, mandate kedaluwarsa tetap tampak aktif di UI sampai ada yang
   mencoba memakainya — dan "aktif" yang salah adalah informasi yang menyesatkan.
2. Menandai eksekusi yang tertinggal di status `running` sebagai `failed`,
   supaya kegagalan proses tidak menyisakan baris yang tampak berjalan selamanya.

Keduanya menulis audit event, karena perubahan status otomatis pun harus
dapat ditelusuri.

    python apps/worker/main.py --once
    python apps/worker/main.py --interval 30
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select  # noqa: E402

from app.database.session import session_scope  # noqa: E402
from app.models.execution import Execution  # noqa: E402
from app.models.governance import Mandate  # noqa: E402
from app.repositories import audit as audit_repo  # noqa: E402


def expire_mandates(now: datetime | None = None) -> int:
    moment = now or datetime.now(timezone.utc)
    expired = 0
    with session_scope() as db:
        candidates = db.scalars(
            select(Mandate).where(Mandate.status.in_(("issued", "approved")))
        ).all()
        for mandate in candidates:
            if mandate.is_usable(moment):
                continue
            if mandate.revoked_at is not None:
                continue
            mandate.status = "expired"
            audit_repo.append_event(
                db,
                event_type="mandate_expired",
                actor="service",
                scope="service",
                action="expire_mandate",
                resource=mandate.id,
                decision="deny",
                plan_id=mandate.plan_id,
                mandate_id=mandate.id,
                detail={"expires_at": mandate.expires_at.isoformat()},
            )
            expired += 1
    return expired


def fail_stuck_executions(older_than_minutes: int = 15, now: datetime | None = None) -> int:
    moment = now or datetime.now(timezone.utc)
    cutoff = moment - timedelta(minutes=older_than_minutes)
    failed = 0
    with session_scope() as db:
        stuck = db.scalars(select(Execution).where(Execution.status == "running")).all()
        for execution in stuck:
            started = execution.started_at
            if started is None:
                continue
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if started > cutoff:
                continue
            execution.status = "failed"
            execution.error = "ditandai gagal oleh worker: melewati batas waktu"
            execution.finished_at = moment
            audit_repo.append_event(
                db,
                event_type="execution_failed",
                actor="service",
                scope="service",
                action="reap_execution",
                resource=execution.id,
                decision="deny",
                plan_id=execution.plan_id,
                mandate_id=execution.mandate_id,
                execution_id=execution.id,
                detail={"reason": "stuck_in_running"},
            )
            failed += 1
    return failed


def run_once(stuck_minutes: int = 15) -> dict:
    return {
        "expired_mandates": expire_mandates(),
        "failed_executions": fail_stuck_executions(stuck_minutes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker pemeliharaan DEXTRA")
    parser.add_argument("--once", action="store_true", help="jalankan sekali lalu keluar")
    parser.add_argument("--interval", type=int, default=30, help="detik antar putaran")
    parser.add_argument("--stuck-minutes", type=int, default=15)
    args = parser.parse_args()

    if args.once:
        print(run_once(args.stuck_minutes))
        return

    print(f"worker berjalan setiap {args.interval}s (Ctrl+C untuk berhenti)")
    while True:
        print(run_once(args.stuck_minutes))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
