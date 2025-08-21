from app.config import get_db_connection
import app.services.sql_queries as queries

def get_allocations(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(queries.SELECT_ALLOCATIONS, (limit,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return rows, columns
