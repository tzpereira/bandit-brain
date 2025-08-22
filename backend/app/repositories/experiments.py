import json
from app.config import get_db_connection
from app.utils import serialize_row

def get_experiments(limit=1000):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, experiment_name, variant_name, impressions, clicks, event_date, context, created_at
        FROM experiments
        ORDER BY event_date DESC, created_at DESC
        LIMIT %s;
        ''',
        (limit,)
    )
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return rows, columns

def get_experiments_by_name_and_date(experiment_name, date):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, experiment_name, variant_name, impressions, clicks, event_date, context, created_at
        FROM experiments
        WHERE experiment_name = %s AND event_date <= %s
        ORDER BY event_date DESC, created_at DESC;
        ''',
        (experiment_name, date)
    )
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [serialize_row(row, columns) for row in rows]

def insert_experiment(data):
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
