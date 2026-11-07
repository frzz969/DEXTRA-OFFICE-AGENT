"""Repository Skill Registry.

Validasi di sini sengaja sempit: hanya aturan yang menentukan otorisasi dan
integritas katalog. Validator manifest lengkap tetap di `packages/skill-registry`
(TypeScript) dan tidak diduplikasi di sini.
"""
from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import CAPABILITIES
from ..database.base import new_id, utcnow
from ..models.registry import (
    RESERVED_SKILL_CAPABILITIES,
    SKILL_TRANSITIONS,
    Skill,
    SkillVersion,
)

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _semver_key(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(version)
    if not match:
        raise SkillError("INVALID_SEMVER", f"Versi bukan semver: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug or ""):
        raise SkillError(
            "INVALID_SLUG", "Slug harus huruf kecil, angka, dan tanda hubung (contoh: kirim-notulen)."
        )
    return slug


def validate_capabilities(capabilities: list[str]) -> tuple[str, ...]:
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise SkillError("UNKNOWN_CAPABILITY", f"Capability tidak dikenal: {capability}")
        if capability in RESERVED_SKILL_CAPABILITIES:
            raise SkillError(
                "PRIVILEGED_CAPABILITY_FORBIDDEN",
                f"Skill tidak boleh meminta capability istimewa: {capability}",
            )
    return tuple(dict.fromkeys(capabilities))


def get_skill(db: Session, *, tenant_id: str, slug: str) -> Skill | None:
    return db.scalar(
        select(Skill).where(
            Skill.slug == slug,
            (Skill.tenant_id == tenant_id) | (Skill.tenant_id.is_(None)),
        )
    )


def list_skills(db: Session, tenant_id: str, *, include_system: bool = True) -> list[Skill]:
    query = select(Skill)
    if include_system:
        query = query.where((Skill.tenant_id == tenant_id) | (Skill.tenant_id.is_(None)))
    else:
        query = query.where(Skill.tenant_id == tenant_id)
    return list(db.scalars(query.order_by(Skill.slug)).all())


def list_versions(db: Session, skill_id: str) -> list[SkillVersion]:
    versions = list(db.scalars(select(SkillVersion).where(SkillVersion.skill_id == skill_id)).all())
    return sorted(versions, key=lambda row: _semver_key(row.version), reverse=True)


def create_skill(
    db: Session,
    *,
    tenant_id: str,
    slug: str,
    display_name: str,
    description: str,
    version: str,
    input_schema: dict,
    output_schema: dict,
    required_capabilities: list[str],
    manifest: dict | None = None,
    created_by_user_id: str | None = None,
    notes: str = "",
) -> tuple[Skill, SkillVersion]:
    validate_slug(slug)
    _semver_key(version)
    capabilities = validate_capabilities(required_capabilities)
    if get_skill(db, tenant_id=tenant_id, slug=slug) is not None:
        raise SkillError("DUPLICATE_SKILL_ID", f"Skill {slug} sudah ada.")
    if not display_name.strip():
        raise SkillError("INVALID_METADATA", "display_name wajib diisi.")

    skill = Skill(
        id=new_id("skl"),
        tenant_id=tenant_id,
        slug=slug,
        display_name=display_name.strip(),
        description=description,
        status="draft",
        latest_version=version,
    )
    db.add(skill)
    db.flush()

    version_row = SkillVersion(
        id=new_id("skv"),
        skill_id=skill.id,
        version=version,
        manifest_json=json.dumps(manifest or {}, sort_keys=True),
        input_schema_json=json.dumps(input_schema, sort_keys=True),
        output_schema_json=json.dumps(output_schema, sort_keys=True),
        required_capabilities_json=json.dumps(list(capabilities)),
        status="draft",
        notes=notes,
        created_by_user_id=created_by_user_id,
    )
    db.add(version_row)
    db.flush()
    return skill, version_row


def add_version(
    db: Session,
    skill: Skill,
    *,
    version: str,
    input_schema: dict,
    output_schema: dict,
    required_capabilities: list[str],
    manifest: dict | None = None,
    created_by_user_id: str | None = None,
    notes: str = "",
) -> SkillVersion:
    _semver_key(version)
    capabilities = validate_capabilities(required_capabilities)
    existing = db.scalar(
        select(SkillVersion).where(SkillVersion.skill_id == skill.id, SkillVersion.version == version)
    )
    if existing is not None:
        raise SkillError("DUPLICATE_VERSION", f"Versi {version} sudah ada.")

    row = SkillVersion(
        id=new_id("skv"),
        skill_id=skill.id,
        version=version,
        manifest_json=json.dumps(manifest or {}, sort_keys=True),
        input_schema_json=json.dumps(input_schema, sort_keys=True),
        output_schema_json=json.dumps(output_schema, sort_keys=True),
        required_capabilities_json=json.dumps(list(capabilities)),
        status="draft",
        notes=notes,
        created_by_user_id=created_by_user_id,
    )
    db.add(row)
    db.flush()
    if skill.latest_version is None or _semver_key(version) > _semver_key(skill.latest_version):
        skill.latest_version = version
    return row


def set_status(db: Session, skill: Skill, new_status: str) -> Skill:
    if new_status not in SKILL_TRANSITIONS:
        raise SkillError("UNKNOWN_STATUS", f"Status tidak dikenal: {new_status}")
    allowed = SKILL_TRANSITIONS[skill.status]
    if new_status not in allowed:
        raise SkillError(
            "INVALID_TRANSITION",
            f"Tidak bisa pindah dari {skill.status} ke {new_status}.",
        )
    skill.status = new_status
    if new_status == "active":
        for row in db.scalars(select(SkillVersion).where(SkillVersion.skill_id == skill.id)).all():
            row.status = "active"
            if row.published_at is None:
                row.published_at = utcnow()
    db.flush()
    return skill
