"""Resource-scope enforcement (A-03) — fondasi.

Token/scope menentukan *apa yang boleh*; resource-scope menentukan *atas apa*.
Keduanya harus lolos. Karena sistem identitas baru separuh (prinsipal hanya ada
di jalur TypeScript, belum di Python), penegakan ini dibuat opt-in: handler yang
memanggil `require_resource_owner` akan menolak akses ke resource yang pemiliknya
tercatat dan tidak cocok; handler yang belum memanggilnya tetap berperilaku lama
(tanpa pemilik = tanpa pemeriksaan), supaya tidak ada regresi diam-diam.

Kontrak:
- `owner_id` None / kosong  -> tidak ada pemilik tercatat -> akses diizinkan
  (perilaku lama, jujur: "belum ada pemilik").
- `owner_id` terisi dan cocok dengan principal pemanggil -> izinkan.
- `owner_id` terisi dan tidak cocok -> tolak 403.
- Pemanggil tanpa principal (token lama) -> jika resource punya pemilik, tolak;
  jika tidak, izinkan (backward compat).
"""
from __future__ import annotations

from fastapi import HTTPException, status

from .security import CallerContext


def resource_allowed(caller: CallerContext, owner_id: str | None) -> bool:
    """Apakah pemanggil boleh mengakses resource dengan owner_id tertentu."""
    if not owner_id:
        # Tidak ada pemilik tercatat -> perilaku lama (tanpa pemeriksaan).
        return True
    principal_id = getattr(caller, "principal_id", None)
    # Principal di Python masih None untuk semua token; kalau principal belum
    # tersedia, pemanggil dengan scope ops yang memegang resource orang lain
    # tetap ditolak bila owner_id tercatat (defense in depth), kecuali scope
    # yang memang punya view_all dan resource tidak dimiliki siapa pun.
    if principal_id is None:
        # Token lama tanpa identitas tidak boleh menyentuh resource berpemilik.
        return False
    return principal_id == owner_id


def require_resource_owner(owner_id: str | None):
    """Dependency factory: 403 bila caller tidak berhak atas owner_id."""

    async def dependency(caller: CallerContext) -> CallerContext:
        if not resource_allowed(caller, owner_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource bukan milik pemanggil.",
            )
        return caller

    return dependency
