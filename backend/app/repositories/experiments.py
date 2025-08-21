import json
from app.config import get_db_connection
import app.services.sql_queries as queries


def get_experiments(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(queries.SELECT_EXPERIMENTS, (limit,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return rows, columns


def insert_experiment(data):
    conn = get_db_connection()
    cur = conn.cursor()
    context_json = json.dumps(data.context) if data.context is not None else None
    cur.execute(
        queries.INSERT_EXPERIMENT,
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
