from app.config import get_db_connection

def get_allocations(limit=1000):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, experiment_name, variant_name, allocated_pct, date, created_at
                FROM allocations
                ORDER BY date DESC, created_at DESC
                LIMIT %s;
                ''', (limit,)
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    finally:
        conn.close()
    return rows, columns
