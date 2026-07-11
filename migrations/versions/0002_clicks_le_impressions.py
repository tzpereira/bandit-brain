"""Enforce clicks <= impressions on experiments

A click-through rate is a probability: you cannot have more clicks than
impressions. The initial schema only checked non-negativity, which let
physically impossible rows (CTR > 100%) into the table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any rows that already violate the invariant so the constraint can be added.
    op.execute("DELETE FROM experiments WHERE clicks > impressions;")
    op.execute(
        "ALTER TABLE experiments ADD CONSTRAINT experiments_clicks_le_impressions CHECK (clicks <= impressions);"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE experiments DROP CONSTRAINT IF EXISTS experiments_clicks_le_impressions;")
