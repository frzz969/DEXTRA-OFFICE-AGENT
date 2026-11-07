"""Paritas kontrak otorisasi antara TypeScript dan Python.

Dua implementasi yang punya pendapat berbeda tentang tool mana yang boleh
dipanggil scope mana adalah bug keamanan, bukan sekadar duplikasi. Tes ini
membaca packages/contracts/src/authorization.ts sebagai sumber kebenaran dan
membandingkannya dengan app/mcp/registry.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTRACT = ROOT / "packages" / "contracts" / "src" / "authorization.ts"
API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.mcp.registry import SCOPE_CAPABILITIES, TOOL_CAPABILITY, tools_for_scope  # noqa: E402


def _parse_ts() -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    source = CONTRACT.read_text(encoding="utf-8")

    tool_block = source.split("TOOL_CAPABILITY", 1)[1].split("} as const", 1)[0]
    tools = dict(re.findall(r"([a-z_]+)\s*:\s*'([a-z_]+)'", tool_block))

    scope_block = source.split("SCOPE_CAPABILITIES", 1)[1].split("};", 1)[0]
    scopes: dict[str, tuple[str, ...]] = {}
    for scope in ("agent", "ops"):
        match = re.search(rf"{scope}\s*:\s*\[(.*?)\]", scope_block, re.S)
        assert match is not None, f"scope {scope} tidak ditemukan di kontrak TS"
        scopes[scope] = tuple(re.findall(r"'([a-z_]+)'", match.group(1)))
    return tools, scopes


def test_contract_file_exists():
    assert CONTRACT.is_file(), f"kontrak tidak ditemukan: {CONTRACT}"


def test_tool_capability_map_is_identical():
    ts_tools, _ = _parse_ts()
    assert ts_tools == TOOL_CAPABILITY, "peta tool->capability menyimpang dari kontrak TypeScript"


def test_scope_capabilities_are_identical():
    _, ts_scopes = _parse_ts()
    assert ts_scopes == SCOPE_CAPABILITIES, "peta scope->capability menyimpang dari kontrak TypeScript"


def test_derived_allowlists_match():
    for scope in ("agent", "ops"):
        expected = sorted(
            name for name, cap in TOOL_CAPABILITY.items() if cap in SCOPE_CAPABILITIES[scope]
        )
        assert tools_for_scope(scope) == expected


def test_unknown_tool_is_never_allowed():
    from app.mcp.registry import scope_allows_tool

    for scope in ("agent", "ops"):
        assert scope_allows_tool(scope, "drop_database") is False
