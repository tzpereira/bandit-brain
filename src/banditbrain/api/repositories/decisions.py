import json

from banditbrain.api.config import get_db_connection
from banditbrain.api.serialization import serialize_row
from banditbrain.core.models import Decision


def insert_decision(decision: Decision, user_id: int) -> None:
    """Persist a served/logged decision. Expects a Decision object."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO decisions (
            decision_id, user_id, experiment_name, variant_name, propensity,
            decision_source, algorithm, policy_params, allocation_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            decision.decision_id,
            user_id,
            decision.experiment_name,
            decision.variant_name,
            decision.propensity,
            decision.decision_source,
            decision.algorithm,
            json.dumps(decision.policy_params) if decision.policy_params is not None else None,
            decision.allocation_date,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_decision(decision_id: str, user_id: int) -> Decision | None:
    """Fetch a decision by id, scoped to the owning user. Returns None if not found."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT decision_id, experiment_name, variant_name, propensity,
               decision_source, algorithm, policy_params, allocation_date, created_at
        FROM decisions
        WHERE decision_id = %s AND user_id = %s;
        """,
        (decision_id, user_id),
    )
    row = cur.fetchone()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    if row is None:
        return None
    return Decision(**serialize_row(row, columns))
