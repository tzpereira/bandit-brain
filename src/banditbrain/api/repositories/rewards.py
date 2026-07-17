import psycopg2

from banditbrain.api.config import get_db_connection
from banditbrain.core.models import Reward


class DuplicateRewardError(Exception):
    """Raised when a decision_id already has a reward recorded (at most one per decision)."""


def insert_reward(reward: Reward, user_id: int) -> None:
    """
    Persist a reward attributed to a decision_id.

    Raises DuplicateRewardError if this decision already has a reward — decisions
    carry at most one reward in this iteration (idempotent handling of retried/
    late-arriving rewards is deferred, see ROADMAP Phase 7).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO rewards (decision_id, user_id, reward) VALUES (%s, %s, %s);",
            (reward.decision_id, user_id, reward.reward),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise DuplicateRewardError(f"Decision {reward.decision_id} already has a reward recorded.") from None
    finally:
        cur.close()
        conn.close()
