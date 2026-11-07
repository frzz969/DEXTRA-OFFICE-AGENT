"""P10-P12 lanjutan: Skill Registry dan workflow orchestration

Satu migrasi untuk empat tabel katalog dan empat tabel eksekusi workflow.
Digabung karena keduanya masuk bersama dan tidak ada deployment di antaranya.

Revision ID: e7b3c9d51a84
Revises: d2a6b8c41f07
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3c9d51a84"
down_revision: Union[str, None] = "d2a6b8c41f07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("latest_version", sa.String(length=32), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_skills_tenant_id_tenants"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("tenant_id", "slug", name="skill_slug"),
    )
    op.create_index(op.f("ix_skills_tenant_id"), "skills", ["tenant_id"], unique=False)
    op.create_index("ix_skills_tenant_status", "skills", ["tenant_id", "status"], unique=False)

    op.create_table(
        "skill_versions",
        sa.Column("skill_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("input_schema_json", sa.Text(), nullable=False),
        sa.Column("output_schema_json", sa.Text(), nullable=False),
        sa.Column("required_capabilities_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_skill_versions_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_skill_versions_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_versions")),
        sa.UniqueConstraint("skill_id", "version", name="skill_version"),
    )
    op.create_index(op.f("ix_skill_versions_skill_id"), "skill_versions", ["skill_id"], unique=False)

    op.create_table(
        "workflow_definitions",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=96), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("steps_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_workflow_definitions_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_workflow_definitions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_definitions")),
        sa.UniqueConstraint("tenant_id", "name", "version", name="workflow_name_version"),
    )
    op.create_index(
        op.f("ix_workflow_definitions_tenant_id"), "workflow_definitions", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_workflow_definitions_tenant_status",
        "workflow_definitions",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_table(
        "workflow_runs",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("checkpoint_json", sa.Text(), nullable=False),
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_workflow_runs_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_workflow_runs_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflow_definitions.id"],
            name=op.f("fk_workflow_runs_workflow_id_workflow_definitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
        sa.UniqueConstraint("idempotency_key", name="workflow_run_idempotency"),
    )
    op.create_index(op.f("ix_workflow_runs_tenant_id"), "workflow_runs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_workflow_id"), "workflow_runs", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_runs_tenant_status", "workflow_runs", ["tenant_id", "status"], unique=False)

    op.create_table(
        "workflow_step_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_workflow_step_runs_run_id_workflow_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_step_runs")),
        sa.UniqueConstraint("run_id", "step_id", name="workflow_step_run"),
    )
    op.create_index(op.f("ix_workflow_step_runs_run_id"), "workflow_step_runs", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_step_runs_run_id"), table_name="workflow_step_runs")
    op.drop_table("workflow_step_runs")
    op.drop_index("ix_workflow_runs_tenant_status", table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_workflow_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_tenant_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index("ix_workflow_definitions_tenant_status", table_name="workflow_definitions")
    op.drop_index(op.f("ix_workflow_definitions_tenant_id"), table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
    op.drop_index(op.f("ix_skill_versions_skill_id"), table_name="skill_versions")
    op.drop_table("skill_versions")
    op.drop_index("ix_skills_tenant_status", table_name="skills")
    op.drop_index(op.f("ix_skills_tenant_id"), table_name="skills")
    op.drop_table("skills")
