"""Audit: append-only di level aplikasi, dengan hash chaining sebagai lapisan tambahan.

`prev_hash` + `entry_hash` membuat penyisipan atau penyuntingan baris lama
terdeteksi saat rantai diverifikasi. Ini bukan pengganti izin database
(REVOKE UPDATE/DELETE), melainkan lapisan kedua — lihat infra/docker untuk
konfigurasi role database.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, IdMixin, utcnow


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"

    seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: agent | ops | dashboard | executor | service — label peran, bukan orang.
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), default="none", server_default="none", nullable=False)
    action: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False)
    resource: Mapped[str] = mapped_column(String(160), default="", server_default="", nullable=False)
    decision: Mapped[str] = mapped_column(String(16), default="", server_default="", nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False, index=True)
    execution_id: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(
        String(64), default="", server_default="", nullable=False, index=True
    )
    detail_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}", nullable=False)
    #: Atribusi tenant. Ditambahkan pada rantai versi 2 — lihat `chain_version`.
    #: Sengaja tanpa foreign key: audit tidak boleh ikut terhapus saat tenant
    #: dihapus, dan baris audit harus tetap terbaca setelah tenant-nya tiada.
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    #: Bentuk payload yang di-hash.
    #: 1 = payload sebelum atribusi tenant (12 kunci, tanpa `tenant_id`).
    #: 2 = payload dengan `tenant_id` ikut di-hash.
    #: Verifikasi memilih aturan menurut angka ini, sehingga rantai lama tetap
    #: sah tanpa menulis ulang hash historis.
    #: Default model disamakan ke "2" agar fresh DB=dari-model (baris baru selalu
    #: versi 2; baris lama sudah tercatat 1 di DB dan tidak ditulis ulang).
    chain_version: Mapped[int] = mapped_column(Integer, default=2, server_default="2", nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    @staticmethod
    def compute_hash(prev_hash: str, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()
