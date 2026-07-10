"""Initial schema: users, experiments, allocations

Revision ID: 0001
Revises:
Create Date: 2026-07-10

"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS experiments (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            experiment_name TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            impressions INT NOT NULL CHECK (impressions >= 0),
            clicks INT NOT NULL CHECK (clicks >= 0),
            cost FLOAT NOT NULL CHECK (cost >= 0),
            event_date DATE NOT NULL,
            context JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_name ON experiments (experiment_name);
        CREATE INDEX IF NOT EXISTS idx_variant_name ON experiments (variant_name);
        CREATE INDEX IF NOT EXISTS idx_event_date ON experiments (event_date);
        CREATE INDEX IF NOT EXISTS idx_context_jsonb ON experiments USING GIN (context);
        CREATE INDEX IF NOT EXISTS idx_experiment_user_id ON experiments (user_id);

        CREATE TABLE IF NOT EXISTS allocations (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            experiment_name TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            allocated_pct FLOAT NOT NULL CHECK (allocated_pct >= 0 AND allocated_pct <= 1),
            algorithm TEXT NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT unique_alloc_variant_date UNIQUE (experiment_name, variant_name, algorithm, date, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_alloc_experiment_name ON allocations (experiment_name);
        CREATE INDEX IF NOT EXISTS idx_alloc_variant_name ON allocations (variant_name);
        CREATE INDEX IF NOT EXISTS idx_alloc_date ON allocations (date);
        CREATE INDEX IF NOT EXISTS idx_alloc_user_id ON allocations (user_id);

        COMMENT ON TABLE users IS 'Stores user accounts for authentication.';
        COMMENT ON TABLE experiments IS 'Stores data about Multi-Armed Bandit experiments, including context.';
        COMMENT ON COLUMN experiments.context IS 'Additional context in JSONB format (e.g., device, location, etc.).';
        COMMENT ON TABLE allocations IS 'Stores traffic allocation recommendations by variant and date.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS allocations; DROP TABLE IF EXISTS experiments; DROP TABLE IF EXISTS users;")
