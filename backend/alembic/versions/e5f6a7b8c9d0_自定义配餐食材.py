"""自定义配餐食材表

Revision ID: e5f6a7b8c9d0
Revises: d4e6f8a0b2c3
Create Date: 2026-11-25 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e6f8a0b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_food_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        sa.Column(
            "food_id",
            sa.Integer(),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.UniqueConstraint(
            "user_id", "date", "meal_type", "food_id", name="uq_meal_food_slot"
        ),
    )
    op.create_index("ix_meal_food_items_user_id", "meal_food_items", ["user_id"])
    op.create_index("ix_meal_food_items_food_id", "meal_food_items", ["food_id"])


def downgrade() -> None:
    op.drop_index("ix_meal_food_items_food_id", table_name="meal_food_items")
    op.drop_index("ix_meal_food_items_user_id", table_name="meal_food_items")
    op.drop_table("meal_food_items")

