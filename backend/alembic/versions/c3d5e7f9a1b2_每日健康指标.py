"""每日健康指标

Revision ID: c3d5e7f9a1b2
Revises: b7c1a2d4e8f0
Create Date: 2026-11-20 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d5e7f9a1b2"
down_revision: str | Sequence[str] | None = "b7c1a2d4e8f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("metric_type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_health_metrics_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_metrics")),
        sa.UniqueConstraint(
            "user_id", "metric_date", "metric_type", name="uq_health_metric"
        ),
    )
    op.create_index(
        op.f("ix_health_metrics_user_id"), "health_metrics", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_metrics_user_id"), table_name="health_metrics")
    op.drop_table("health_metrics")
