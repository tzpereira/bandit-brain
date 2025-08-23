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
        SELECT id, experiment_name, variant_name, impressions, clicks, event_date, context, created_at
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
    date: Optional[str] = None
) -> List[Metric]:
    """
    Returns aggregated metrics (impressions, clicks, CTR) for each variant, with optional filters.
    Returns a list of dicts: variant_name, impressions, clicks, ctr.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = '''
        SELECT
            variant_name,
            SUM(impressions) AS impressions,
            SUM(clicks) AS clicks,
            CASE WHEN SUM(impressions) > 0 THEN CAST(SUM(clicks) AS FLOAT) / SUM(impressions) ELSE 0 END AS ctr
        FROM experiments
    '''
    params = []
    where_clauses = []

    if experiment_name:
        where_clauses.append('experiment_name = %s')
        params.append(experiment_name)
    if date:
        where_clauses.append('event_date <= %s')
        params.append(date)
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' GROUP BY variant_name ORDER BY variant_name;'
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    metrics = [
        {
            "variant_name": row[0],
            "impressions": row[1],
            "clicks": row[2],
            "ctr": row[3]
        } for row in rows
    ]
    return [Metric(**m) for m in metrics]


def insert_experiment(data: Experiment) -> None:
    """
    Inserts a new experiment record into the database.
    Expects an Experiment object.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    context_json = json.dumps(data.context) if data.context is not None else None

    cur.execute(
        '''
        INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, event_date, context)
        VALUES (%s, %s, %s, %s, %s, %s);
        ''',
        (
            data.experiment_name,
            data.variant_name,
            data.impressions,
            data.clicks,
            data.event_date,
            context_json,
        )
    )
    conn.commit()
    cur.close()
    conn.close()


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
            d.event_date,
            json.dumps(d.context) if d.context is not None else None
        )
        for d in data_list
    ]
    cur.executemany(
        '''
        INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, event_date, context)
        VALUES (%s, %s, %s, %s, %s, %s);
        ''',
        values
    )
    conn.commit()
    cur.close()
    conn.close()