"""Konfigurasi runtime DEXTRA v2.

Dibaca dari environment setiap kali dipakai, bukan saat modul dimuat, supaya
rotasi token dan perubahan DATABASE_URL tidak menuntut restart proses.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def repo_root() -> Path:
    """Lokasi root monorepo, bukan CWD proses.

    ``DEXTRA_ROOT`` bisa menimpanya (mis. saat image Docker menyalin kode ke
    lokasi lain). Default diturunkan dari lokasi berkas ini:
    ``<root>/apps/api/app/core/config.py``.
    """
    override = os.environ.get("DEXTRA_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[4]


def data_dir() -> Path:
    """Direktori data runtime (SQLite, outbox). Dibuat bila belum ada."""
    path = Path(_env("DEXTRA_DATA_DIR", str(repo_root() / "data"))).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_database_url() -> str:
    return f"sqlite+pysqlite:///{(data_dir() / 'dextra.db').as_posix()}"


@dataclass(frozen=True)
class Settings:
    database_url: str
    agent_token: str
    ops_token: str
    allowed_origins: tuple[str, ...]
    environment: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    # --- P8: sesi manusia ---
    session_cookie_name: str
    csrf_cookie_name: str
    #: Batas absolut. Tidak pernah diperpanjang oleh aktivitas.
    session_absolute_minutes: int
    #: Batas idle. Diperpanjang saat sesi dipakai.
    session_idle_minutes: int
    #: Cookie `Secure` hanya dimatikan di lingkungan pengembangan lokal.
    cookie_secure: bool
    login_max_failures: int
    login_window_minutes: int
    login_lock_minutes: int
    mfa_issuer: str
    mfa_encryption_key: str

    # --- P9 lanjutan: pengikatan tenant untuk token gateway lama ---
    #: Slug tenant yang diwakili `DEXTRA_AGENT_TOKEN` / `DEXTRA_OPS_TOKEN`.
    #: Kosong = tidak terikat; token lalu tidak bisa menyentuh data ber-tenant.
    legacy_tenant_slug: str

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_development(self) -> bool:
        return self.environment in ("development", "test")


_DEV_AGENT_TOKEN = "agent-dev-token"
_DEV_OPS_TOKEN = "ops-dev-token"


def _validate_production_secrets(environment: str, agent_token: str, ops_token: str) -> None:
    """A23: env-only secrets di production mode.

    Nilai default dev tetap ada untuk development/test (TIDAK diubah diam-diam),
    tetapi bila DEXTRA_ENV=production dan token gateway masih default, startup
    ditolak eksplisit — jangan sampai token publik menjadi kredensial produksi.
    """
    if environment.strip().lower() != "production":
        return
    problems = []
    if agent_token == _DEV_AGENT_TOKEN:
        problems.append("DEXTRA_AGENT_TOKEN masih default dev")
    if ops_token == _DEV_OPS_TOKEN:
        problems.append("DEXTRA_OPS_TOKEN masih default dev")
    if problems:
        raise RuntimeError(
            "A23 production mode: token gateway memakai default dev ("
            + "; ".join(problems)
            + "). Set env eksplisit sebelum start; default dev tidak boleh dipakai di production."
        )


def get_settings() -> Settings:
    raw_origins = _env(
        "DEXTRA_ALLOWED_ORIGINS",
        "http://127.0.0.1:8899,http://localhost:8899,http://127.0.0.1:3000,http://localhost:3000",
    )
    origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
    environment = _env("DEXTRA_ENV", "development")
    _validate_production_secrets(
        environment,
        _env("DEXTRA_AGENT_TOKEN", _DEV_AGENT_TOKEN),
        _env("DEXTRA_OPS_TOKEN", _DEV_OPS_TOKEN),
    )
    return Settings(
        database_url=_env("DATABASE_URL", default_database_url()),
        agent_token=_env("DEXTRA_AGENT_TOKEN", _DEV_AGENT_TOKEN),
        ops_token=_env("DEXTRA_OPS_TOKEN", _DEV_OPS_TOKEN),
        allowed_origins=origins,
        environment=environment,
        google_client_id=_env("GOOGLE_CLIENT_ID", ""),
        google_client_secret=_env("GOOGLE_CLIENT_SECRET", ""),
        google_redirect_uri=_env("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/auth/google/callback"),
        session_cookie_name=_env("DEXTRA_SESSION_COOKIE", "dextra_session"),
        csrf_cookie_name=_env("DEXTRA_CSRF_COOKIE", "dextra_csrf"),
        session_absolute_minutes=int(_env("DEXTRA_SESSION_ABSOLUTE_MINUTES", "720")),
        session_idle_minutes=int(_env("DEXTRA_SESSION_IDLE_MINUTES", "30")),
        # Default aman: `Secure` aktif kecuali eksplisit di lingkungan lokal.
        cookie_secure=_env(
            "DEXTRA_COOKIE_SECURE",
            "false" if environment in ("development", "test") else "true",
        ).lower()
        in ("1", "true", "yes", "on"),
        login_max_failures=int(_env("DEXTRA_LOGIN_MAX_FAILURES", "5")),
        login_window_minutes=int(_env("DEXTRA_LOGIN_WINDOW_MINUTES", "15")),
        login_lock_minutes=int(_env("DEXTRA_LOGIN_LOCK_MINUTES", "15")),
        mfa_issuer=_env("DEXTRA_MFA_ISSUER", "DEXTRA"),
        mfa_encryption_key=_env("DEXTRA_MFA_KEY", ""),
        legacy_tenant_slug=_env("DEXTRA_LEGACY_TENANT", "").strip(),
    )
