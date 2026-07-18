"""Add users.is_demo for a hard-guarded read-only public demo account

Phase 4 (public demo) needs a designated account that visitors can log into
and explore, without being able to mutate or destroy its data. is_demo flags
that account; write/destructive routes (see api/guardrails.py) reject
requests from a flagged user unless a server-side bypass secret is presented
(used only by scripts/seed.py and scripts/reset_demo_data.py to refresh it).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-18

"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;
        COMMENT ON COLUMN users.is_demo IS 'Read-only public demo account - write routes reject it.';
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_demo;")
