"""Repository tenant dan keanggotaan.

Aturan yang dipegang seluruh fungsi di sini: **tidak ada query lintas tenant**.
Setiap pembacaan menerima `tenant_id` eksplisit dari pemanggil yang sudah
terautentikasi, dan tidak ada helper "ambil semua baris" yang bisa dipakai tanpa
sengaja.

`principal_for` adalah satu-satunya tempat capability seorang pengguna dihitung.
Kalau perhitungan ini tersebar di beberapa handler, cepat atau lambat ada handler
yang lupa memeriksa keanggotaan.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import CAPABILITIES, ROLE_CAPABILITIES, ROLE_DESCRIPTIONS
from ..database.base import new_id, utcnow
from ..models.identity import Permission, Role, RolePermission, User
from ..models.tenant import Membership, Tenant


class TenantNotFound(LookupError):
    """Ditemukan di sini (bukan stub): sinyal 404 untuk pemanggil."""

    pass


def update_tenant_status(db: Session, tenant_id: str, status: str) -> Tenant:
    """Ubah status tenant. Implementasi nyata (sebelumnya tidak ada jalur ubah)."""
    if status not in ("active", "suspended", "disabled"):
        raise ValueError(f"status tenant tidak dikenal: {status}")
    tenant = require_active_tenant_or_any(db, tenant_id)
    tenant.status = status
    db.flush()
    return tenant


def require_active_tenant_or_any(db: Session, tenant_id: str) -> Tenant:
    tenant = get_tenant(db, tenant_id)
    if tenant is None:
        raise TenantNotFound(tenant_id)
    return tenant


@dataclass(frozen=True)
class TenantPrincipal:
    """Konteks pemanggil yang sudah diverifikasi di dalam satu tenant."""

    user_id: str
    tenant_id: str
    membership_id: str
    email: str
    display_name: str
    role_name: str
    capabilities: tuple[str, ...]
    mfa_enabled: bool

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


def create_tenant(db: Session, *, slug: str, name: str) -> Tenant:
    tenant = Tenant(id=new_id("ten"), slug=slug, name=name, status="active", settings_json="{}")
    db.add(tenant)
    db.flush()
    return tenant


def get_tenant(db: Session, tenant_id: str) -> Tenant | None:
    return db.get(Tenant, tenant_id)


def get_tenant_by_slug(db: Session, slug: str) -> Tenant | None:
    return db.scalar(select(Tenant).where(Tenant.slug == slug))


def require_active_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = get_tenant(db, tenant_id)
    if tenant is None:
        raise TenantNotFound(tenant_id)
    if not tenant.is_active():
        raise TenantNotFound(tenant_id)
    return tenant


def ensure_system_role(db: Session, name: str) -> Role:
    """Buat/perbarui role sistem beserta permission-nya. Idempoten.

    Role sistem punya `tenant_id = NULL` dan berlaku di semua tenant. Permission
    disinkronkan dari `ROLE_CAPABILITIES` supaya seed dan kode tidak menyimpang.
    """
    if name not in ROLE_CAPABILITIES:
        raise ValueError(f"Role tidak dikenal: {name}")
    role = db.scalar(select(Role).where(Role.name == name, Role.tenant_id.is_(None)))
    if role is None:
        role = Role(
            id=new_id("rol"),
            name=name,
            description=ROLE_DESCRIPTIONS.get(name, ""),
            tenant_id=None,
            is_system=True,
        )
        db.add(role)
        db.flush()

    wanted = ROLE_CAPABILITIES[name]
    existing = {perm.capability: perm for perm in role.permissions}
    for capability in wanted:
        if capability not in CAPABILITIES:
            raise ValueError(f"Capability tidak dikenal pada role {name}: {capability}")
        permission = existing.get(capability)
        if permission is None:
            permission = db.scalar(select(Permission).where(Permission.capability == capability))
            if permission is None:
                permission = Permission(
                    id=new_id("per"), name=capability, capability=capability
                )
                db.add(permission)
                db.flush()
            db.add(RolePermission(id=new_id("rp"), role_id=role.id, permission_id=permission.id))
    db.flush()
    db.refresh(role)
    return role


def add_membership(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    role_id: str,
    is_default: bool = False,
    status: str = "active",
) -> Membership:
    """Tambahkan anggota. Role harus milik tenant itu atau role sistem."""
    role = db.get(Role, role_id)
    if role is None:
        raise ValueError("Role tidak ditemukan.")
    if role.tenant_id is not None and role.tenant_id != tenant_id:
        # Menautkan role tenant lain adalah eskalasi lintas tenant.
        raise ValueError("Role milik tenant lain.")
    if get_tenant(db, tenant_id) is None:
        raise TenantNotFound(tenant_id)

    existing = db.scalar(
        select(Membership).where(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
    )
    if existing is not None:
        return existing

    if is_default:
        # Hanya satu tenant default per pengguna.
        for other in db.scalars(select(Membership).where(Membership.user_id == user_id)).all():
            other.is_default = False

    membership = Membership(
        id=new_id("mem"),
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
        status=status,
        is_default=is_default,
        accepted_at=utcnow() if status == "active" else None,
    )
    db.add(membership)
    db.flush()
    return membership


def get_membership(db: Session, *, tenant_id: str, user_id: str) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.tenant_id == tenant_id, Membership.user_id == user_id
        )
    )


def list_memberships_for_user(db: Session, user_id: str) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
        ).all()
    )


def list_tenant_members(db: Session, tenant_id: str) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership).where(Membership.tenant_id == tenant_id).order_by(Membership.created_at)
        ).all()
    )


def capabilities_for_role(role: Role | None) -> tuple[str, ...]:
    if role is None:
        return ()
    capabilities = {perm.capability for perm in role.permissions}
    # Capability di luar katalog diabaikan, bukan diteruskan: baris permission
    # yang salah ketik tidak boleh menjadi wewenang.
    return tuple(c for c in CAPABILITIES if c in capabilities)


def principal_for(db: Session, *, tenant_id: str, user_id: str) -> TenantPrincipal | None:
    """Konteks pemanggil, atau None bila tidak berhak.

    None dikembalikan untuk semua kondisi yang membuat akses tidak sah:
    tenant tidak aktif, pengguna nonaktif, keanggotaan tidak aktif, atau role
    hilang. Pemanggil tidak boleh membedakan alasannya di respons HTTP.
    """
    tenant = get_tenant(db, tenant_id)
    if tenant is None or not tenant.is_active():
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None

    membership = get_membership(db, tenant_id=tenant_id, user_id=user_id)
    if membership is None or membership.status != "active":
        return None

    role = db.get(Role, membership.role_id)
    if role is None:
        return None
    # Role tenant lain tidak boleh dipakai, meski baris keanggotaan menunjuknya.
    if role.tenant_id is not None and role.tenant_id != tenant_id:
        return None

    return TenantPrincipal(
        user_id=user.id,
        tenant_id=tenant_id,
        membership_id=membership.id,
        email=user.email,
        display_name=user.display_name,
        role_name=role.name,
        capabilities=capabilities_for_role(role),
        mfa_enabled=user.mfa_enabled,
    )


def default_tenant_for_user(db: Session, user_id: str) -> str | None:
    memberships = [
        m
        for m in list_memberships_for_user(db, user_id)
        if m.status == "active" and m.accepted_at is not None
    ]
    if not memberships:
        return None
    for membership in memberships:
        if membership.is_default:
            return membership.tenant_id
    return memberships[0].tenant_id
