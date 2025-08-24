from app.utils import serialize_row
from app.config import get_db_connection
from typing import Optional, List
from app.models import Allocation


def get_allocations(
    experiment_name: Optional[str] = None,
    date: Optional[str] = None,
    algorithm: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Allocation]:
    """
    Retrieve allocation records, optionally filtered by experiment_name and date.
    Returns a list of dicts with all columns.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = '''
        SELECT id, experiment_name, variant_name, allocated_pct, algorithm, date, created_at
        FROM allocations
    '''
    params = []
    where_clauses = []

    if experiment_name:
        where_clauses.append('experiment_name = %s')
        params.append(experiment_name)
    if date:
        where_clauses.append('date = %s')
        params.append(date)
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' ORDER BY date DESC, created_at DESC'
    if limit:
        query += ' LIMIT %s'
        params.append(limit)
    query += ';'

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [Allocation(**serialize_row(row, columns)) for row in rows]


def insert_allocation(data: Allocation) -> None:
    """
    Inserts a new allocation record into the database.
    Expects an Allocation object.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO allocations (experiment_name, variant_name, allocated_pct, algorithm, date)
        VALUES (%s, %s, %s, %s, %s);
        ''',
        (
            data.experiment_name,
            data.variant_name,
            data.allocated_pct,
            data.algorithm,
            data.date,
        )
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_allocations_batch(data_list: List[Allocation]) -> None:
    """
    Inserts multiple allocation records into the database in a single batch.
    Expects a list of Allocation objects.
    """
    if not data_list:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    values = [
        (
            d.experiment_name,
            d.variant_name,
            d.allocated_pct,
            d.algorithm,
            d.date
        )
        for d in data_list
    ]
    cur.executemany(
        '''
        INSERT INTO allocations (experiment_name, variant_name, allocated_pct, algorithm, date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (experiment_name, variant_name, algorithm, date)
        DO UPDATE SET allocated_pct = EXCLUDED.allocated_pct, created_at = NOW();
        ''',
        values
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_allocations():
    """
    Delete all allocation records from the database.
    TODO: Implement conditional deletion based on parameters.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM allocations;")
    conn.commit()
    cur.close()
    conn.close()