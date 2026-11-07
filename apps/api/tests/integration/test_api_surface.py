"""Permukaan API: rute yang benar-benar terpasang, dan tidak ada yang terbuka.

Berkas ini menjawab satu pertanyaan yang tidak dijawab tes per-fitur: kalau
frontend memanggil endpoint yang tertulis di kontrak, apakah endpoint itu ada,
dan apakah ia menolak pemanggil tanpa kredensial?

Daftar rute diambil dari skema OpenAPI aplikasi, bukan dari dokumen. Dengan
begitu tes ini gagal bila sebuah router lupa didaftarkan di `main.py`, dan juga
gagal bila endpoint baru muncul tanpa disengaja terbuka.
"""
from __future__ import annotations

import pytest

#: Endpoint yang memang boleh diakses tanpa kredensial.
PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/google",
    "/api/v1/auth/google/callback",
}

#: Endpoint yang mengembalikan 2xx tanpa kredensial **karena tidak ada yang
#: bisa dicabut**: logout tanpa cookie sesi adalah no-op, bukan kebocoran.
#: Bila cookie sesi ada, permintaan ini tetap wajib CSRF (diuji di
#: `test_auth_flow.py`), sehingga pemaksaan logout lintas situs tetap tertutup.
NO_OP_PATHS = {
    ("POST", "/api/v1/auth/logout"),
}

#: Rute yang wajib ada supaya frontend P7–P12 bisa hidup. Diambil dari
#: `docs/API-CONTRACT-P7-P12.md`; kalau dokumen dan kode berbeda, tes ini gagal.
REQUIRED_ROUTES = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/auth/session"),
    ("POST", "/api/v1/auth/mfa/enroll"),
    ("POST", "/api/v1/auth/mfa/activate"),
    ("POST", "/api/v1/auth/mfa/verify"),
    ("POST", "/api/v1/auth/mfa/disable"),
    ("POST", "/api/v1/auth/password"),
    ("GET", "/api/v1/auth/sessions"),
    ("POST", "/api/v1/auth/sessions/{session_id}/revoke"),
    ("GET", "/api/v1/tokens"),
    ("POST", "/api/v1/tokens"),
    ("POST", "/api/v1/tokens/{token_id}/revoke"),
    ("POST", "/api/v1/tokens/{token_id}/rotate"),
    ("GET", "/api/v1/service-accounts"),
    ("POST", "/api/v1/service-accounts"),
    ("GET", "/api/v1/service-accounts/{service_account_id}"),
    ("POST", "/api/v1/service-accounts/{service_account_id}/revoke"),
    ("GET", "/api/v1/security/overview"),
    ("GET", "/api/v1/security/events"),
    ("GET", "/api/v1/security/login-history"),
    ("GET", "/api/v1/security/sessions"),
    ("POST", "/api/v1/security/sessions/{session_id}/revoke"),
    ("GET", "/api/v1/security/tokens"),
    ("GET", "/api/v1/security/service-identities"),
    ("GET", "/api/v1/security/mfa-status"),
    ("GET", "/api/v1/users"),
    ("GET", "/api/v1/roles"),
    ("GET", "/api/v1/permissions"),
    ("GET", "/api/v1/skills"),
    ("POST", "/api/v1/skills"),
    ("GET", "/api/v1/skills/{slug}"),
    ("POST", "/api/v1/skills/{slug}/versions"),
    ("POST", "/api/v1/skills/{slug}/status"),
    ("GET", "/api/v1/workflows"),
    ("POST", "/api/v1/workflows"),
    ("POST", "/api/v1/workflows/{workflow_id}/activate"),
    ("POST", "/api/v1/workflows/{workflow_id}/runs"),
    ("GET", "/api/v1/workflows/runs"),
    ("GET", "/api/v1/workflows/runs/{run_id}"),
    ("POST", "/api/v1/workflows/runs/{run_id}/gates/{step_id}/approve"),
    ("POST", "/api/v1/workflows/runs/{run_id}/resume"),
    ("GET", "/api/v1/office-agent/plans"),
    ("POST", "/api/v1/office-agent/plans"),
    ("GET", "/api/v1/office-agent/plans/{plan_id}"),
    ("POST", "/api/v1/office-agent/plans/{plan_id}/actions/{action_id}/approve"),
    ("GET", "/api/v1/meta"),
}


def _routes(app) -> set[tuple[str, str]]:
    spec = app.openapi()
    return {
        (method.upper(), path)
        for path, operations in spec["paths"].items()
        for method in operations
    }


def _concrete(path: str) -> str:
    """Ganti parameter path dengan nilai dummy agar rute benar-benar cocok."""
    out = []
    for part in path.split("/"):
        out.append("x_probe" if part.startswith("{") else part)
    return "/".join(out)


def test_required_routes_are_mounted(app):
    mounted = _routes(app)
    missing = sorted(REQUIRED_ROUTES - mounted)
    assert not missing, f"rute kontrak belum terpasang: {missing}"


def test_no_api_route_is_reachable_without_credentials(app, client):
    """Setiap endpoint non-publik harus menolak pemanggil anonim.

    Batas yang diterima 401 (belum terautentikasi) atau 403 (CSRF lebih dulu
    menolak permintaan yang mengubah keadaan). Yang tidak boleh: 2xx.
    """
    leaked = []
    for method, path in sorted(_routes(app)):
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            continue
        if (method, path) in NO_OP_PATHS:
            continue
        response = client.request(method, _concrete(path), json={})
        if response.status_code < 400:
            leaked.append((method, path, response.status_code))
    assert not leaked, f"endpoint dapat diakses tanpa kredensial: {leaked}"


def test_anonymous_rejection_is_not_a_server_error(app, client):
    """Penolakan harus terklasifikasi, bukan 500 karena bug di jalur auth."""
    broken = []
    for method, path in sorted(_routes(app)):
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            continue
        response = client.request(method, _concrete(path), json={})
        if response.status_code >= 500:
            broken.append((method, path, response.status_code))
    assert not broken, f"endpoint gagal 5xx saat anonim: {broken}"


def test_meta_requires_authentication(client):
    assert client.get("/api/v1/meta").status_code == 401


def test_unbacked_capabilities_are_computed_from_reality(client, ops_headers):
    """Klaim 'belum tersedia' harus berasal dari penegak yang benar-benar ada."""
    body = client.get("/api/v1/meta", headers=ops_headers).json()
    #: Sejak PATCH/DELETE policy ada, `edit_policy` punya penegak nyata — jadi
    #: daftar "belum tersedia" harus kosong, bukan tetap menyebutnya.
    assert body["unbacked_capabilities"] == []
    assert "edit_policy" in body["enforced_capabilities"]
    # P10/P11 sudah menegakkan dua capability ini; menyebutnya "belum tersedia"
    # adalah klaim palsu yang dulu benar-benar dikirim ke frontend.
    assert "manage_users" in body["enforced_capabilities"]
    assert "manage_integrations" in body["enforced_capabilities"]
    assert "manage_users" not in body["unbacked_capabilities"]


def test_permissions_endpoint_reports_the_same_truth(client, ops_headers):
    body = client.get("/api/v1/permissions", headers=ops_headers).json()
    assert body["unbacked_capabilities"] == []
    assert "edit_policy" in body["enforced_capabilities"]
    assert set(body["all_capabilities"]) >= set(body["enforced_capabilities"])


def test_cors_preflight_allows_dashboard_origin_with_credentials(client):
    """Dashboard memakai cookie, jadi preflight harus mengizinkan kredensial."""
    origin = "http://127.0.0.1:8899"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_rejects_unknown_origin(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_openapi_document_is_generated(app):
    """Kontrak mesin harus bisa diambil frontend tanpa menjalankan server."""
    spec = app.openapi()
    assert spec["info"]["version"] == "2.0.0"
    assert "/api/v1/office-agent/plans" in spec["paths"]


def test_contract_document_lists_exactly_the_served_routes(app):
    """Blok rute di dokumen harus sama dengan yang benar-benar dilayani.

    Tanpa tes ini, dokumen kontrak akan menyimpang perlahan: rute ditambah,
    dokumen tidak. Frontend membaca dokumen, jadi dokumen yang salah sama
    merusaknya dengan endpoint yang tidak ada.
    """
    from pathlib import Path
    import re

    doc = Path(__file__).resolve().parents[4] / "docs" / "API-CONTRACT-P7-P12.md"
    text = doc.read_text(encoding="utf-8")
    marker = "## 10. Daftar rute terverifikasi"
    assert marker in text, "bagian daftar rute terverifikasi hilang dari kontrak"

    block = text.split(marker, 1)[1]
    documented = set()
    for line in block.splitlines():
        match = re.match(r"^(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)$", line.strip())
        if match:
            documented.add((match.group(1), match.group(2)))

    assert documented == _routes(app), (
        "dokumen kontrak tidak sama dengan rute yang dilayani; "
        f"hanya di kode: {sorted(_routes(app) - documented)}; "
        f"hanya di dokumen: {sorted(documented - _routes(app))}"
    )
