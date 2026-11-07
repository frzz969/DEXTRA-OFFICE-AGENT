"""Identitas dan permission.

Halaman /users dan /permissions di dashboard terkunci karena capability-nya
belum punya backend. Di sini kejujuran itu ditegakkan: /permissions melaporkan
konteks pemanggil apa adanya, dan /users menolak dengan 403 karena
`manage_users` tidak diberikan ke scope mana pun.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...database.base import new_id
from ...repositories import audit as audit_repo
from ...core.security import (
    CAPABILITIES,
    SCOPE_CAPABILITIES,
    CallerContext,
    get_caller,
    enforced_capabilities,
    require_capability,
    unbacked_capabilities,
)
from ...core.authz import require_tenant
from ...database.session import get_db
from ...models.identity import Permission, Role, RolePermission, User
from ...models.tenant import MEMBERSHIP_STATUSES, Membership
from ...repositories import tenants as tenant_repo

router = APIRouter(tags=["identity"])


@router.get("/permissions")
def permissions(caller: CallerContext = Depends(get_caller)) -> dict:
    return {
        "scope": caller.scope,
        "principal": caller.principal,
        "capabilities": list(caller.capabilities),
        "enforced_capabilities": list(enforced_capabilities()),
        "unbacked_capabilities": list(unbacked_capabilities()),
        "all_capabilities": list(CAPABILITIES),
        "scope_capabilities": {k: list(v) for k, v in SCOPE_CAPABILITIES.items()},
        "note": "Tidak ada identitas per pengguna: token membawa wewenang, bukan nama.",
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Anggota tenant pemanggil. Tidak ada jalur ke pengguna tenant lain.

    Daftar ini sebelumnya mengembalikan seluruh tabel `users`. Begitu `admin`
    memegang `manage_users`, query tanpa filter tenant akan menjadi kebocoran —
    jadi filternya ada di sini, bukan di UI.
    """
    tenant_id = require_tenant(caller)
    rows = db.execute(
        select(Membership, User, Role)
        .join(User, User.id == Membership.user_id)
        .join(Role, Role.id == Membership.role_id)
        .where(Membership.tenant_id == tenant_id)
        .order_by(User.email)
    ).all()
    return {
        "items": [
            {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": role.name,
                "status": membership.status,
                "is_default": membership.is_default,
                "joined_at": membership.created_at.isoformat(),
            }
            for membership, user, role in rows
        ],
        "tenant_id": tenant_id,
    }


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    tenant_id = require_tenant(caller)
    rows = db.scalars(
        select(Role)
        .where((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
        .order_by(Role.name)
    ).all()
    return {
        "items": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "capabilities": sorted(perm.capability for perm in role.permissions),
            }
            for role in rows
        ]
    }


# --- Mutasi anggota & role (manage_users, audit, tenant-scoped) ---


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=64)
    status: str = Field(default="invited", max_length=16)


class UpdateUserRequest(BaseModel):
    role: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=16)
    display_name: str | None = Field(default=None, max_length=120)


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=255)
    capabilities: list[str] = Field(default_factory=list)


class UpdateRoleRequest(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=255)
    capabilities: list[str] | None = None


def _resolve_role(db: Session, tenant_id: str, role_name: str) -> Role:
    """Role sistem (tenant NULL) atau role milik tenant ini. Role tenant
    lain tidak pernah resolve: itu eskalasi lintas tenant."""
    role = db.scalar(
        select(Role).where(
            Role.name == role_name,
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
        )
    )
    if role is None:
        # Role sistem didefinisikan di kode (ROLE_CAPABILITIES): pastikan
        # barisnya ada daripada 404 untuk role yang memang dikenal sistem.
        from ...core.security import ROLE_CAPABILITIES

        if role_name in ROLE_CAPABILITIES:
            role = tenant_repo.ensure_system_role(db, role_name)
        else:
            raise HTTPException(status_code=404, detail=f"Role tidak ditemukan: {role_name}")
    return role


def _serialize_member(db: Session, membership: Membership) -> dict:
    user = db.get(User, membership.user_id)
    role = db.get(Role, membership.role_id)
    return {
        "id": user.id if user else membership.user_id,
        "user_id": membership.user_id,
        "email": user.email if user else "",
        "display_name": user.display_name if user else "",
        "role": role.name if role else "",
        "status": membership.status,
        "is_default": membership.is_default,
        "tenant_id": membership.tenant_id,
    }


def _validate_capabilities(capabilities: list[str]) -> None:
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise HTTPException(status_code=422, detail=f"Capability tidak dikenal: {capability}")


def _set_role_capabilities(db: Session, role: Role, capabilities: list[str]) -> None:
    _validate_capabilities(capabilities)
    db.execute(RolePermission.__table__.delete().where(RolePermission.role_id == role.id))
    db.flush()
    for capability in sorted(set(capabilities)):
        permission = db.scalar(select(Permission).where(Permission.capability == capability))
        if permission is None:
            permission = Permission(id=new_id("per"), name=capability, capability=capability)
            db.add(permission)
            db.flush()
        db.add(RolePermission(id=new_id("rp"), role_id=role.id, permission_id=permission.id))
    db.flush()
    db.refresh(role)


@router.post("/users", status_code=201)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Tambah anggota ke tenant pemanggil. User baru dibuat tanpa password
    (status invited default) — tidak ada kredensial default yang diam-diam."""
    tenant_id = require_tenant(caller)
    if payload.status not in MEMBERSHIP_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status tidak dikenal: {payload.status}")
    role = _resolve_role(db, tenant_id, payload.role)
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        user = User(
            id=new_id("usr"),
            email=payload.email,
            display_name=payload.display_name,
            is_active=True,
        )
        db.add(user)
        db.flush()
    existing = tenant_repo.get_membership(db, tenant_id=tenant_id, user_id=user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Pengguna sudah menjadi anggota tenant ini.")
    membership = tenant_repo.add_membership(
        db, tenant_id=tenant_id, user_id=user.id, role_id=role.id, status=payload.status
    )
    audit_repo.append_event(
        db,
        event_type="member_added",
        actor=caller.email or caller.display_name or caller.scope,
        scope=caller.scope,
        action="add_member",
        resource=user.id,
        decision="allow",
        tenant_id=tenant_id,
        detail={"email": user.email, "role": role.name, "status": payload.status},
    )
    db.commit()
    return _serialize_member(db, membership)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Ubah role/status/nama anggota tenant pemanggil. Anggota tenant lain
    menjawab 404."""
    tenant_id = require_tenant(caller)
    membership = tenant_repo.get_membership(db, tenant_id=tenant_id, user_id=user_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Anggota tidak ditemukan.")
    changes: dict[str, str] = {}
    if payload.role is not None:
        role = _resolve_role(db, tenant_id, payload.role)
        membership.role_id = role.id
        changes["role"] = role.name
    if payload.status is not None:
        if payload.status not in MEMBERSHIP_STATUSES:
            raise HTTPException(status_code=422, detail=f"Status tidak dikenal: {payload.status}")
        membership.status = payload.status
        changes["status"] = payload.status
    if payload.display_name is not None:
        user = db.get(User, user_id)
        if user is not None:
            user.display_name = payload.display_name
            changes["display_name"] = payload.display_name
    audit_repo.append_event(
        db,
        event_type="member_updated",
        actor=caller.email or caller.display_name or caller.scope,
        scope=caller.scope,
        action="update_member",
        resource=user_id,
        decision="allow",
        tenant_id=tenant_id,
        detail=changes,
    )
    db.commit()
    return _serialize_member(db, membership)


@router.post("/roles", status_code=201)
def create_role(
    payload: CreateRoleRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Buat role kustom milik tenant pemanggil (bukan role sistem)."""
    tenant_id = require_tenant(caller)
    _validate_capabilities(payload.capabilities)
    existing = db.scalar(
        select(Role).where(
            Role.name == payload.name,
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Role sudah ada: {payload.name}")
    role = Role(
        id=new_id("rol"),
        name=payload.name,
        description=payload.description,
        tenant_id=tenant_id,
        is_system=False,
    )
    db.add(role)
    db.flush()
    _set_role_capabilities(db, role, payload.capabilities)
    audit_repo.append_event(
        db,
        event_type="role_created",
        actor=caller.email or caller.display_name or caller.scope,
        scope=caller.scope,
        action="create_role",
        resource=role.id,
        decision="allow",
        tenant_id=tenant_id,
        detail={"name": role.name, "capabilities": sorted(set(payload.capabilities))},
    )
    db.commit()
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "capabilities": sorted(perm.capability for perm in role.permissions),
    }


@router.patch("/roles/{role_id}")
def update_role(
    role_id: str,
    payload: UpdateRoleRequest,
    db: Session = Depends(get_db),
    caller: CallerContext = Depends(require_capability("manage_users")),
) -> dict:
    """Ubah role kustom tenant pemanggil. Role sistem tidak boleh diubah."""
    tenant_id = require_tenant(caller)
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan.")
    if role.is_system or role.tenant_id is None:
        raise HTTPException(status_code=409, detail="Role sistem tidak boleh diubah.")
    if role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan.")
    changes: dict[str, str] = {}
    if payload.name is not None:
        role.name = payload.name
        changes["name"] = payload.name
    if payload.description is not None:
        role.description = payload.description
        changes["description"] = payload.description
    if payload.capabilities is not None:
        _set_role_capabilities(db, role, payload.capabilities)
        changes["capabilities"] = ",".join(sorted(set(payload.capabilities)))
    audit_repo.append_event(
        db,
        event_type="role_updated",
        actor=caller.email or caller.display_name or caller.scope,
        scope=caller.scope,
        action="update_role",
        resource=role.id,
        decision="allow",
        tenant_id=tenant_id,
        detail=changes,
    )
    db.commit()
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "capabilities": sorted(perm.capability for perm in role.permissions),
    }


# --- Google OAuth (fondasi; status honest: butuh env GOOGLE_CLIENT_ID/SECRET) ---

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


@router.get("/auth/google")
def google_login() -> dict:
    """OAuth dicabut secara eksplisit sampai sesi bisa diterbitkan dengan benar.

    Keputusan A15: session belum siap (tidak ada alur: state terverifikasi,
    tukar code->id_token dengan validasi exp/aud/iss/email_verified, lalu
    buat session cookie). Daripada mengembalikan principal tanpa sesi — yang
    memberi kesan login berhasil — endpoint ini menjawab 503 jujur.
    Response netral: tidak membocorkan konfigurasi server.
    """
    raise HTTPException(
        status_code=503,
        detail="Login Google belum tersedia.",
    )


@router.get("/auth/google/callback")
def google_callback(code: str = Query(...), state: str | None = None) -> dict:
    """Lihat google_login. Callback tidak menukar code apa pun."""
    raise HTTPException(
        status_code=503,
        detail="Login Google belum tersedia.",
    )
