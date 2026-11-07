"""Otorisasi tingkat resource: batas tenant pada data tata kelola.

`core.security` menjawab "boleh melakukan apa". Modul ini menjawab "atas data
siapa". Keduanya harus lolos; capability tanpa batas tenant berarti satu approver
di tenant A bisa menyetujui rencana tenant B.

Tiga perilaku yang disengaja:

1. **Pemanggil terikat tenant tidak pernah melihat baris tanpa tenant.** Baris
   lama (sebelum P9) tidak diatribusikan, jadi tidak boleh ditebak.
2. **Ketidakcocokan menghasilkan 404, bukan 403.** 403 mengonfirmasi bahwa
   resource itu ada; 404 tidak.
3. **Pemanggil tanpa tenant tidak melihat apa pun.** Token gateway lama dulu
   melewati seluruh pemeriksaan dan karena itu membaca data semua tenant. Itu
   bukan kompatibilitas, itu kebocoran. Sekarang jalur ini gagal-tertutup;
   agar tetap berfungsi, ikat tokennya lewat `DEXTRA_LEGACY_TENANT` (lihat
   `core.security._bind_legacy_tenant`).
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import Select, false

from .security import CallerContext

LEGACY_SCOPE_NOTE = (
    "Token gateway (DEXTRA_AGENT_TOKEN/DEXTRA_OPS_TOKEN) hanya melihat tenant "
    "yang disebut DEXTRA_LEGACY_TENANT; tanpa itu, ia tidak melihat data "
    "ber-tenant sama sekali."
)


def caller_tenant(caller: CallerContext) -> str | None:
    return caller.tenant_id


def scope_to_tenant(statement: Select, model, caller: CallerContext) -> Select:
    """Batasi query ke tenant pemanggil.

    Pemanggil tanpa tenant mendapat query yang tidak mungkin cocok. Mengembalikan
    statement apa adanya — perilaku sebelumnya — berarti "tanpa tenant" dibaca
    sebagai "semua tenant", dan itulah yang membuat token gateway bisa membaca
    mandate tenant lain.
    """
    tenant_id = caller_tenant(caller)
    if tenant_id is None:
        return statement.where(false())
    return statement.where(model.tenant_id == tenant_id)


def assert_tenant_access(caller: CallerContext, resource_tenant_id: str | None, *, resource: str = "Resource") -> None:
    """404 bila resource tidak berada di tenant pemanggil.

    Pemanggil tanpa tenant juga mendapat 404: tidak ada tenant yang bisa
    dicocokkan, jadi tidak ada resource yang boleh dibuka.
    """
    tenant_id = caller_tenant(caller)
    if tenant_id is None or resource_tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"{resource} tidak ditemukan.")


def require_tenant(caller: CallerContext) -> str:
    """Untuk endpoint yang tidak masuk akal tanpa tenant (mis. administrasi)."""
    if caller.tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Endpoint ini membutuhkan identitas yang terikat tenant.",
        )
    return caller.tenant_id
