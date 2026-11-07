"""Registri tool MCP sisi Python.

Cermin dari packages/contracts/src/authorization.ts. Dua server tidak boleh
punya pendapat berbeda tentang tool mana yang boleh dipanggil scope mana;
`tests/security/test_authorization_parity.py` membandingkannya dengan berkas
TypeScript supaya penyimpangan langsung gagal, bukan ditemukan saat demo.
"""
from __future__ import annotations

from typing import Final

TOOL_CAPABILITY: Final[dict[str, str]] = {
    "get_org_rules": "view_all",
    "find_precedent": "view_all",
    "create_plan": "create_request",
    # Intake lengkap Office Agent (normalisasi -> dekomposisi -> klarifikasi ->
    # plan). Membuat permintaan/plan, jadi kewenangannya sama dengan create_plan.
    "office_agent_run": "create_request",
    "validate_plan": "create_request",
    "get_plan": "view_all",
    "list_plans": "view_all",
    # Challenge sekali pakai sebelum submit_approval: kodenya dicetak ke terminal
    # server, tidak pernah dikembalikan ke peramban. Kewenangannya sama dengan
    # menyetujui, karena ia hanya menerbitkan kode untuk keputusan yang sama.
    "request_approval_challenge": "approve",
    "submit_approval": "approve",
    "get_mandate": "view_all",
    "list_mandates": "view_all",
    "issue_mandate": "issue_mandate",
    "execute_action": "execute",
    "revoke_mandate": "revoke_mandate",
    "list_executions": "view_all",
    "get_status": "view_all",
    "get_audit_log": "view_audit",
    # Ekspor audit: kewenangannya sama dengan membaca audit. Menulis artefak
    # baru bukan menulis audit, jadi tidak perlu capability baru.
    "export_audit": "view_audit",
    # Baca riwayat pengiriman alert. Read-only: tidak ada tool yang mengirim,
    # karena pengiriman adalah akibat dari sesuatu yang sudah terjadi, bukan
    # tindakan yang bisa diminta pemanggil.
    "list_alerts": "view_audit",
    "get_caller_context": "view_own",
    "list_specialists": "view_all",
}

SCOPE_CAPABILITIES: Final[dict[str, tuple[str, ...]]] = {
    "agent": ("view_own", "view_all", "create_request"),
    "ops": (
        "view_own",
        "view_all",
        "create_request",
        "approve",
        "issue_mandate",
        "revoke_mandate",
        "execute",
        "view_audit",
    ),
}


def tools_for_scope(scope: str) -> list[str]:
    caps = SCOPE_CAPABILITIES.get(scope, ())
    return sorted(name for name, cap in TOOL_CAPABILITY.items() if cap in caps)


def scope_allows_tool(scope: str, tool: str) -> bool:
    cap = TOOL_CAPABILITY.get(tool)
    if cap is None:
        return False
    return cap in SCOPE_CAPABILITIES.get(scope, ())
