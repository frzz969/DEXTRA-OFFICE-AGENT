"""Aplikasi FastAPI DEXTRA v2.

Semua endpoint di bawah /api/v1. Tidak ada endpoint yang terbuka tanpa
autentikasi — termasuk /overview, karena ringkasan operasional tetap informasi
internal. Pengecualian hanya /health, yang tidak mengembalikan data bisnis.

Dua jalur masuk yang sah: sesi cookie (manusia) dan bearer token (API token
atau token gateway MCP). Keduanya berakhir di `core.security.get_caller`.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.csrf import CsrfMiddleware
from .middleware.tenant import TenantContextMiddleware
from .core.security import (
    CAPABILITIES,
    CallerContext,
    enforced_capabilities,
    get_caller,
    unbacked_capabilities,
)
from .database.session import database_health
from .modules.alerts.router import router as alerts_router
from .modules.analytics.router import router as analytics_router
from .modules.data_management.router import router as data_management_router
from .modules.integrations.router import router as integrations_router
from .modules.search.router import router as search_router
from .modules.settings.router import router as settings_router
from .modules.approvals.router import router as approvals_router
from .modules.audit.router import router as audit_router
from .modules.auth.router import router as auth_router
from .modules.conversations.router import router as conversations_router
from .modules.execution.router import router as execution_router
from .modules.identity.router import router as identity_router
from .modules.mandates.router import router as mandates_router
from .modules.office_agent.router import router as office_agent_router
from .modules.overview.router import router as overview_router
from .modules.policies.router import router as policies_router
from .modules.security_center.router import router as security_center_router
from .modules.skills.router import router as skills_router
from .modules.workflows.router import router as workflows_router
from .modules.service_accounts.router import router as service_accounts_router
from .modules.tokens.router import router as tokens_router
from .modules.tasks.router import router as tasks_router
from .modules.workforce.router import router as workforce_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DEXTRA API",
        version="2.0.0",
        description="Governed Enterprise AI Workforce & Operations Platform",
    )

    # Allowlist eksplisit. Tidak ada "*" — wildcard CORS pada API yang memegang
    # wewenang eksekusi akan membatalkan seluruh pemisahan scope.
    #
    # `allow_credentials` aktif karena sesi manusia memakai cookie. Ini aman
    # justru karena origin-nya daftar tertutup: kredensial hanya dikirim ke
    # origin yang sudah ditentukan, bukan ke sembarang situs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    # Tenant context seeding (additive, non-breaking). Runs inside CORS,
    # outermost-safe but before CSRF? Placed right after CORS per spec.
    app.add_middleware(TenantContextMiddleware)
    for router in (
        auth_router,
        overview_router,
        workforce_router,
        tasks_router,
        execution_router,
        approvals_router,
        mandates_router,
        policies_router,
        audit_router,
        identity_router,
        tokens_router,
        service_accounts_router,
        security_center_router,
        skills_router,
        workflows_router,
        office_agent_router,
        conversations_router,
        integrations_router,
        settings_router,
        analytics_router,
        search_router,
        alerts_router,
        data_management_router,
    ):
        app.include_router(router, prefix=API_PREFIX)

    # CSRF dipasang setelah router supaya berlaku untuk seluruh endpoint tanpa
    # perlu diingat di setiap route baru.
    app.add_middleware(CsrfMiddleware)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        db = database_health()
        return {
            "ok": db["ok"],
            "service": "dextra-api",
            "version": "2.0.0",
            "database": db,
            "environment": settings.environment,
        }

    @app.get(f"{API_PREFIX}/meta", tags=["meta"])
    def meta(caller: CallerContext = Depends(get_caller)) -> dict:
        """Intropeksi kontrak. Ikut terautentikasi seperti endpoint lain.

        `unbacked_capabilities` dihitung dari capability yang benar-benar
        dipasang (dependency HTTP + tool MCP), bukan dari daftar tulis tangan
        yang cepat basi.
        """
        return {
            "api_prefix": API_PREFIX,
            "capabilities": list(CAPABILITIES),
            "enforced_capabilities": list(enforced_capabilities()),
            "unbacked_capabilities": list(unbacked_capabilities()),
            "auth_kind": caller.auth_kind,
        }

    return app


app = create_app()
