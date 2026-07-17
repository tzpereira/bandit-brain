import json

from banditbrain.api.config import get_db_connection
from banditbrain.api.serialization import serialize_row
from banditbrain.core.models import Experiment, Metric
from banditbrain.core.stats import standard_error, wilson_score_interval


def get_experiments(
    user_id: int, experiment_name: str | None = None, date: str | None = None, limit: int | None = None
) -> list[Experiment]:
    """
    Retrieve experiment records, optionally filtered by experiment_name and date.
    Returns a list of Experiment objects.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT id, experiment_name, variant_name, impressions, clicks, cost, event_date, context, created_at
        FROM experiments
    """
    params = []
    where_clauses = []

    where_clauses.append("user_id = %s")
    params.append(user_id)

    if experiment_name:
        where_clauses.append("experiment_name = %s")
        params.append(experiment_name)
    if date:
        where_clauses.append("event_date = %s")
        params.append(date)
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY id ASC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    query += ";"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [serialize_row(row, columns) for row in rows]


def get_experiments_metrics(
    user_id: int, experiment_name: str | None = None, date: str | None = None, group_by_context: bool = False
) -> list[Metric]:
    """
    Retrieve aggregated metrics for experiments, optionally filtered by experiment_name and date.

    This is the "learn" half of the serve -> log -> learn loop: when group_by_context
    is False, served traffic (decisions logged via POST /decide, outcomes attributed
    via POST /reward) is folded in alongside batch-ingested data, so the next
    /recommend call reflects live traffic. Served decisions carry no context
    breakdown yet (contextual decisioning is a later phase), so the per-context view
    (group_by_context=True) reflects batch-ingested data only.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    if group_by_context:
        group_fields = "variant_name, context->>'device', context->>'location', context->>'user_segment'"
        select_fields = """
            variant_name,
            COALESCE(context->>'device', 'unknown') AS device,
            COALESCE(context->>'location', 'unknown') AS location,
            COALESCE(context->>'user_segment', 'unknown') AS user_segment,
        """
        order_fields = "variant_name, device, location, user_segment"
    else:
        group_fields = "variant_name"
        select_fields = """
            variant_name,
            'all' AS device,
            'all' AS location,
            'all' AS user_segment,
        """
        order_fields = "variant_name"

    params: list = []
    where_clauses = ["user_id = %s"]
    params.append(user_id)
    if experiment_name:
        where_clauses.append("experiment_name = %s")
        params.append(experiment_name)
    if date:
        where_clauses.append("event_date <= %s")
        params.append(date)
    where_clause = "WHERE " + " AND ".join(where_clauses)

    served_cte = ""
    served_union = ""
    if not group_by_context:
        served_where_clauses = ["d.user_id = %s"]
        params.append(user_id)
        if experiment_name:
            served_where_clauses.append("d.experiment_name = %s")
            params.append(experiment_name)
        if date:
            served_where_clauses.append("d.created_at::date <= %s")
            params.append(date)
        served_where = "WHERE " + " AND ".join(served_where_clauses)
        served_cte = f"""
        , served AS (
            SELECT
                d.variant_name,
                'all' AS device,
                'all' AS location,
                'all' AS user_segment,
                COALESCE(SUM(r.reward), 0) AS clicks,
                0::float AS total_cost,
                COUNT(d.decision_id) AS impressions
            FROM decisions d
            LEFT JOIN rewards r ON r.decision_id = d.decision_id
            {served_where}
            GROUP BY d.variant_name
        )
        """
        served_union = "UNION ALL SELECT * FROM served"

    query = f"""
        WITH ingested AS (
            SELECT
                {select_fields}
                SUM(clicks) AS clicks,
                SUM(cost) AS total_cost,
                SUM(impressions) AS impressions
            FROM experiments
            {where_clause}
            GROUP BY {group_fields}
        ){served_cte},
        agg AS (
            SELECT
                variant_name, device, location, user_segment,
                SUM(clicks) AS clicks,
                SUM(total_cost) AS total_cost,
                SUM(impressions) AS impressions
            FROM (
                SELECT * FROM ingested
                {served_union}
            ) combined
            GROUP BY variant_name, device, location, user_segment
        )
        SELECT variant_name, clicks, total_cost, impressions, device, location, user_segment
        FROM agg
        ORDER BY {order_fields};
    """

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    metrics = []
    for variant_name, clicks, total_cost, impressions, device, location, user_segment in rows:
        clicks = int(clicks)
        impressions = int(impressions)
        ci_lower, ci_upper = wilson_score_interval(clicks, impressions)
        metrics.append(
            Metric(
                variant_name=variant_name,
                clicks=clicks,
                total_cost=total_cost,
                impressions=impressions,
                device=device,
                location=location,
                user_segment=user_segment,
                cpc=total_cost / clicks if clicks > 0 else None,
                cpv=total_cost / impressions if impressions > 0 else None,
                ctr=clicks / impressions if impressions > 0 else 0.0,
                ctr_se=standard_error(clicks, impressions),
                ctr_ci_lower=ci_lower,
                ctr_ci_upper=ci_upper,
            )
        )
    return metrics


def insert_experiments_batch(user_id: int, experiments: list[Experiment]) -> None:
    """
    Inserts multiple experiment records into the database in a single batch.
    Expects a list of Experiment objects.
    """
    if not experiments:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    values = [
        (
            user_id,
            d.experiment_name,
            d.variant_name,
            d.impressions,
            d.clicks,
            d.cost,
            d.event_date,
            json.dumps(d.context) if d.context is not None else None,
        )
        for d in experiments
    ]
    cur.executemany(
        """
        INSERT INTO experiments (user_id, experiment_name, variant_name, impressions, clicks, cost, event_date, context)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        values,
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_experiments(user_id: int):
    """
    Delete all experiment records from the database.
    TODO: Implement conditional deletion based on parameters.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM experiments WHERE user_id = %s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
