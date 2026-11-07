"""Seed data DEXTRA v2.

Seed ini sengaja kecil dan jujur: hanya empat spesialis yang benar-benar
ditetapkan (§8.4), satu organisasi, dan satu kebijakan contoh. Tidak ada angka
operasional karangan — kalau tabel kosong, UI harus menampilkan empty state,
bukan data palsu.

Idempoten: menjalankan dua kali tidak menggandakan baris.

    python packages/database/seeds/seed.py --reset
    python -m app.seed --reset            # dari apps/api
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_DIR = ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.passwords import hash_password  # noqa: E402
from app.core.security import ROLE_CAPABILITIES  # noqa: E402
from app.database.base import Base, new_id  # noqa: E402
from app.database.session import get_engine, session_scope  # noqa: E402
from app.models.identity import Role, User  # noqa: E402
from app.models.governance import Policy, PolicyVersion  # noqa: E402
from app.models.tasks import Task, WorkPackage  # noqa: E402
from app.models.workforce import Agent, AgentCapability, AgentVersion  # noqa: E402
from app.repositories import credentials as credential_repo  # noqa: E402
from app.repositories import tenants as tenant_repo  # noqa: E402

SPECIALISTS = [
    {
        "slug": "workforce-dispatcher",
        "display_name": "Workforce Dispatcher",
        "agent_type": "orchestrator",
        "description": "Membagi pekerjaan ke spesialis dan memantau kemajuannya.",
        "capabilities": ["route_task", "read_workforce"],
    },
    {
        "slug": "executive-assistant",
        "display_name": "Executive Assistant",
        "agent_type": "assistant",
        "description": "Menyusun rencana kerja dan ringkasan untuk manusia.",
        "capabilities": ["create_plan", "read_calendar"],
    },
    {
        "slug": "administrative-officer",
        "display_name": "Administrative Officer",
        "agent_type": "operator",
        "description": "Menyiapkan dokumen dan korespondensi sesuai mandat.",
        "capabilities": ["draft_document"],
    },
    {
        "slug": "adversarial-reviewer",
        "display_name": "Adversarial Reviewer",
        "agent_type": "reviewer",
        "description": "Mencari cacat rencana sebelum diajukan untuk persetujuan.",
        "capabilities": ["review_plan"],
    },
]

#: Role tidak lagi didefinisikan di sini. Sumber tunggalnya
#: `core.security.ROLE_CAPABILITIES`, dipakai bersama oleh seed dan repository.
#: Dua daftar role yang terpisah adalah cara paling mudah membuat seed memberi
#: wewenang yang tidak dikenal kode.
DEMO_TENANT = {"slug": "dextra-demo", "name": "DEXTRA Demo"}

#: Pengguna demo. Password TIDAK ditulis di sini. Kalau `DEXTRA_SEED_PASSWORD`
#: diisi, password itu yang dipakai; kalau tidak, seed membuat password acak dan
#: mencetaknya sekali ke stdout. Tidak ada kredensial default yang bisa ditebak.
DEMO_USERS = [
    ("budi.santoso@dextra.local", "Budi Santoso", "approver"),
    ("sari.wijaya@dextra.local", "Sari Wijaya", "operator"),
    ("auditor@dextra.local", "Auditor Internal", "auditor"),
]


def _seed_password() -> tuple[str, bool]:
    """Kembalikan (password, dibuat_otomatis)."""
    import os
    import secrets

    configured = os.environ.get("DEXTRA_SEED_PASSWORD")
    if configured:
        return configured, False
    return secrets.token_urlsafe(12), True



def _free_id(db, model, preferred: str, prefix: str) -> str:
    """ID deterministik bila masih kosong; ID acak bila sudah dipakai.

    Baris legacy (tenant NULL) bisa memegang ID yang sama dengan yang akan dibuat
    seed. Seed tidak boleh menimpanya, jadi ia memilih ID lain — bukan mengambil
    alih baris itu.
    """
    if db.get(model, preferred) is None:
        return preferred
    return new_id(prefix)


def seed(reset: bool = False) -> dict:
    engine = get_engine()
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    counts = {
        "agents": 0,
        "roles": 0,
        "tenants": 0,
        "users": 0,
        "service_accounts": 0,
        "policies": 0,
        "work_packages": 0,
        "tasks": 0,
    }

    with session_scope() as db:
        # Tenant demo dulu: id-nya dipakai untuk atribusi baris lain di run ini.
        tenant = tenant_repo.get_tenant_by_slug(db, DEMO_TENANT["slug"])
        if tenant is None:
            tenant = tenant_repo.create_tenant(db, slug=DEMO_TENANT["slug"], name=DEMO_TENANT["name"])
            counts["tenants"] += 1

        for spec in SPECIALISTS:
            #: Hanya baris milik tenant ini yang dicocokkan. Baris legacy dengan
            #: `tenant_id IS NULL` tidak dimiliki siapa pun: mengambilnya alih
            #: berarti memberi satu tenant data yang mungkin milik tenant lain.
            agent = db.scalar(
                select(Agent).where(Agent.slug == spec["slug"], Agent.tenant_id == tenant.id)
            )
            if agent is None:
                agent = Agent(
                    id=_free_id(db, Agent, f"agt_{spec['slug']}", "agt"),
                    slug=spec["slug"],
                    tenant_id=tenant.id,
                    display_name=spec["display_name"],
                    agent_type=spec["agent_type"],
                    description=spec["description"],
                    status="idle",
                )
                db.add(agent)
                db.flush()
                counts["agents"] += 1
            for capability in spec["capabilities"]:
                exists = db.scalar(
                    select(AgentCapability).where(
                        AgentCapability.agent_id == agent.id,
                        AgentCapability.capability == capability,
                    )
                )
                if exists is None:
                    db.add(
                        AgentCapability(
                            id=_free_id(db, AgentCapability, f"cap_{agent.id}_{capability}", "cap"),
                            agent_id=agent.id,
                            capability=capability,
                        )
                    )
            if not agent.versions:
                db.add(
                    AgentVersion(
                        id=_free_id(db, AgentVersion, f"ver_{agent.id}_1", "ver"),
                        agent_id=agent.id,
                        version=1,
                        config_json='{"source":"seed"}',
                        notes="Versi awal dari seed.",
                    )
                )

        for name in ROLE_CAPABILITIES:
            already = db.scalar(select(Role).where(Role.name == name, Role.tenant_id.is_(None)))
            tenant_repo.ensure_system_role(db, name)
            if already is None:
                counts["roles"] += 1

        # --- Tenant demo, anggota, dan identitas mesin ---
        tenant = tenant_repo.get_tenant_by_slug(db, DEMO_TENANT["slug"])
        if tenant is None:
            tenant = tenant_repo.create_tenant(db, slug=DEMO_TENANT["slug"], name=DEMO_TENANT["name"])
            counts["tenants"] += 1

        password, generated = _seed_password()
        for email, display_name, role_name in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    id=f"usr_{email.split('@')[0].replace('.', '_')}",
                    email=email,
                    display_name=display_name,
                    is_active=True,
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
                counts["users"] += 1
            role = db.scalar(select(Role).where(Role.name == role_name, Role.tenant_id.is_(None)))
            if role is None:
                raise SystemExit(f"Role sistem belum ada: {role_name}")
            tenant_repo.add_membership(
                db,
                tenant_id=tenant.id,
                user_id=user.id,
                role_id=role.id,
                is_default=True,
            )

        if not credential_repo.list_service_accounts(db, tenant.id):
            credential_repo.create_service_account(
                db,
                tenant_id=tenant.id,
                name="office-agent-worker",
                kind="worker",
                scopes=["view_own", "view_all", "create_request", "execute"],
                description="Worker Office Agent. Identitas mesin, bukan akun manusia.",
            )
            counts["service_accounts"] += 1

        if generated and counts["users"]:
            # Dicetak sekali, tidak disimpan di mana pun. Kalau baris ini terlewat,
            # password tidak bisa dipulihkan — dan itu memang tujuannya.
            print(
                "Password demo dibuat otomatis (set DEXTRA_SEED_PASSWORD untuk memilih sendiri):",
                password,
            )
        elif generated:
            # Pengguna demo sudah ada; password yang baru dibuat tidak dipakai
            # siapa pun. Mencetaknya akan menyesatkan: tampak seperti kredensial
            # yang bisa dipakai login, padahal tidak tersimpan di baris mana pun.
            print("Pengguna demo sudah ada; password tidak diubah.")

        policy = db.scalar(
            select(Policy).where(Policy.slug == "recipient-scope", Policy.tenant_id == tenant.id)
        )
        if policy is None:
            policy = Policy(
                id=_free_id(db, Policy, "pol_recipient_scope", "pol"),
                slug="recipient-scope",
                title="Penerima di luar scope organisasi",
                scope="organization",
                tenant_id=tenant.id,
            )
            db.add(policy)
            db.flush()
            db.add(
                PolicyVersion(
                    id=_free_id(db, PolicyVersion, "pov_recipient_scope_1", "pov"),
                    policy_id=policy.id,
                    version=1,
                    rules_json='{"deny_when":"recipient outside allowed_recipients"}',
                    change_note="Versi awal dari seed.",
                )
            )
            counts["policies"] += 1

        package = db.scalar(
            select(WorkPackage).where(
                WorkPackage.title == "Onboarding vendor Q4", WorkPackage.tenant_id == tenant.id
            )
        )
        if package is None:
            package = WorkPackage(
                id=_free_id(db, WorkPackage, "wpg_onboarding_q4", "wpg"),
                title="Onboarding vendor Q4",
                status="draft",
                priority="normal",
                tenant_id=tenant.id,
            )
            db.add(package)
            db.flush()
            counts["work_packages"] += 1
            for index, title in enumerate(
                ("Kumpulkan dokumen vendor", "Verifikasi rekening", "Kirim surat perkenalan"), start=1
            ):
                db.add(
                    Task(
                        id=_free_id(db, Task, f"tsk_onboarding_q4_{index}", "tsk"),
                        work_package_id=package.id,
                        title=title,
                        status="todo",
                        sort_order=index,
                        tenant_id=tenant.id,
                    )
                )
                counts["tasks"] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database DEXTRA v2")
    parser.add_argument("--reset", action="store_true", help="hapus seluruh tabel lalu isi ulang")
    args = parser.parse_args()
    counts = seed(reset=args.reset)
    print("Seed selesai:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
