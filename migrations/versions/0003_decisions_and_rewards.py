"""Add decisions/rewards tables and allocations.params for the serve/log/learn loop

The batch /recommend -> /decide -> /reward loop needs each allocation batch to carry
the policy params it was computed with (the "policy version" a served decision is
replayed against), plus two new tables:

- decisions: one row per POST /decide call — the chosen arm, its propensity
  P(arm | state), provenance (served vs. byo), and the policy version + batch date
  it was sampled from. This is what makes a decision replayable/auditable.
- rewards: one row per POST /reward call, attributing a binary outcome to a
  decision_id. UNIQUE on decision_id — at most one reward per decision for now;
  idempotent handling of retried/late-arriving rewards is deferred (see ROADMAP
  Phase 7, non-goal for this iteration).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE allocations ADD COLUMN IF NOT EXISTS params JSONB;

        CREATE TABLE IF NOT EXISTS decisions (
            decision_id TEXT PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            experiment_name TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            propensity FLOAT NOT NULL CHECK (propensity >= 0 AND propensity <= 1),
            decision_source TEXT NOT NULL CHECK (decision_source IN ('served', 'byo')),
            algorithm TEXT NOT NULL,
            policy_params JSONB,
            allocation_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_user_id ON decisions (user_id);
        CREATE INDEX IF NOT EXISTS idx_decisions_experiment_name ON decisions (experiment_name);
        CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions (created_at);

        CREATE TABLE IF NOT EXISTS rewards (
            id SERIAL PRIMARY KEY,
            decision_id TEXT NOT NULL UNIQUE REFERENCES decisions(decision_id),
            user_id INT NOT NULL REFERENCES users(id),
            reward FLOAT NOT NULL CHECK (reward IN (0.0, 1.0)),
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rewards_user_id ON rewards (user_id);

        COMMENT ON COLUMN allocations.params IS 'Policy params this batch used - the policy version.';
        COMMENT ON TABLE decisions IS 'One row per served decision: arm, propensity, provenance, policy version.';
        COMMENT ON TABLE rewards IS 'Outcomes attributed to a decision_id. Binary (0/1), one per decision.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS rewards;
        DROP TABLE IF EXISTS decisions;
        ALTER TABLE allocations DROP COLUMN IF EXISTS params;
        """
    )
