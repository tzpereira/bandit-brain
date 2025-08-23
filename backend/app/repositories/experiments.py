import json
from typing import Optional, List
from app.models import Metric
from app.config import get_db_connection
from app.utils import serialize_row
from app.models import Experiment


def get_experiments(
    experiment_name: Optional[str] = None,
    date: Optional[str] = None,
    limit: Optional[int] = 10000
) -> List[Experiment]:
    """
    Retrieve experiment records, optionally filtered by experiment_name and date.
    Returns a list of Experiment objects.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = '''
        SELECT id, experiment_name, variant_name, impressions, clicks, cost, event_date, context, created_at
        FROM experiments
    '''
    params = []
    where_clauses = []

    if experiment_name:
        where_clauses.append('experiment_name = %s')
        params.append(experiment_name)
    if date:
        where_clauses.append('event_date = %s')
        params.append(date)
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' ORDER BY event_date DESC, created_at DESC'
    if limit:
        query += ' LIMIT %s'
        params.append(limit)
    query += ';'

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [serialize_row(row, columns) for row in rows]


def get_experiments_metrics(
    experiment_name: Optional[str] = None,
    date: Optional[str] = None,
    group_by_context: bool = False
) -> List[Metric]:
    """
    Retrieve aggregated metrics for experiments, optionally filtered by experiment_name and date.
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

    query = f'''
        WITH agg AS (
            SELECT
                {select_fields}
                SUM(clicks) AS clicks,
                SUM(cost) AS total_cost,
                SUM(impressions) AS impressions
            FROM experiments
            {{where_clause}}
            GROUP BY {group_fields}
        )
        SELECT
            variant_name,
            clicks,
            total_cost,
            impressions,
            device,
            location,
            user_segment,
            CASE WHEN clicks > 0 THEN total_cost / clicks ELSE NULL END AS cpc,
            CASE WHEN impressions > 0 THEN total_cost / impressions ELSE NULL END AS cpv,
            CASE WHEN impressions > 0 THEN clicks::float / impressions ELSE 0 END AS ctr,
            CASE WHEN impressions > 0 THEN
                SQRT((clicks::float / impressions) * (1 - (clicks::float / impressions)) / impressions)
            ELSE 0 END AS ctr_se,
            CASE WHEN impressions > 0 THEN
                GREATEST((clicks::float / impressions) - 1.96 * SQRT((clicks::float / impressions) * (1 - (clicks::float / impressions)) / impressions), 0)
            ELSE 0 END AS ctr_ci_lower,
            CASE WHEN impressions > 0 THEN
                (clicks::float / impressions) + 1.96 * SQRT((clicks::float / impressions) * (1 - (clicks::float / impressions)) / impressions)
            ELSE 0 END AS ctr_ci_upper
        FROM agg
        ORDER BY {order_fields};
    '''

    params = []
    where_clauses = []

    if experiment_name:
        where_clauses.append('experiment_name = %s')
        params.append(experiment_name)
    if date:
        where_clauses.append('event_date <= %s')
        params.append(date)

    where_clause = ''
    if where_clauses:
        where_clause = 'WHERE ' + ' AND '.join(where_clauses)

    query = query.format(where_clause=where_clause)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    metrics = [
        {
            "variant_name": row[0],
            "clicks": row[1],
            "total_cost": row[2],
            "impressions": row[3],
            "device": row[4],
            "location": row[5],
            "user_segment": row[6],
            "cpc": row[7],
            "cpv": row[8],
            "ctr": row[9],
            "ctr_se": row[10],
            "ctr_ci_lower": row[11],
            "ctr_ci_upper": row[12]
        } for row in rows
    ]
    return [Metric(**m) for m in metrics]


def insert_experiments_batch(data_list: List[Experiment]) -> None:
    """
    Inserts multiple experiment records into the database in a single batch.
    Expects a list of Experiment objects.
    """
    if not data_list:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    values = [
        (
            d.experiment_name,
            d.variant_name,
            d.impressions,
            d.clicks,
            d.cost,
            d.event_date,
            json.dumps(d.context) if d.context is not None else None
        )
        for d in data_list
    ]
    cur.executemany(
        '''
        INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, cost, event_date, context)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        ''',
        values
    )
    conn.commit()
    cur.close()
    conn.close()