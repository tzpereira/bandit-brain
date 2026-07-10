from banditbrain.api.config import get_db_connection
from banditbrain.api.serialization import serialize_row
from banditbrain.core.models import Allocation


def get_allocations(
    user_id: int,
    experiment_name: str | None = None,
    date: str | None = None,
    algorithm: str | None = None,
    limit: int | None = None,
) -> list[Allocation]:
    """
    Retrieve allocation records, optionally filtered by experiment_name and date.
    Returns a list of dicts with all columns.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT id, experiment_name, variant_name, allocated_pct, algorithm, date, created_at
        FROM allocations
    """
    params = []
    where_clauses = []

    where_clauses.append("user_id = %s")
    params.append(user_id)

    if experiment_name:
        where_clauses.append("experiment_name = %s")
        params.append(experiment_name)
    if date:
        where_clauses.append("date = %s")
        params.append(date)
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY date DESC, created_at DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    query += ";"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [Allocation(**serialize_row(row, columns)) for row in rows]


def insert_allocation(data: Allocation, user_id: int) -> None:
    """
    Inserts a new allocation record into the database.
    Expects an Allocation object.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO allocations (user_id, experiment_name, variant_name, allocated_pct, algorithm, date)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            user_id,
            data.experiment_name,
            data.variant_name,
            data.allocated_pct,
            data.algorithm,
            data.date,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_allocations_batch(allocations: list[Allocation], user_id: int) -> None:
    """
    Inserts multiple allocation records into the database in a single batch.
    Expects a list of Allocation objects.
    """
    if not allocations:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    values = [(user_id, d.experiment_name, d.variant_name, d.allocated_pct, d.algorithm, d.date) for d in allocations]
    cur.executemany(
        """
        INSERT INTO allocations (user_id, experiment_name, variant_name, allocated_pct, algorithm, date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, experiment_name, variant_name, algorithm, date)
        DO UPDATE SET allocated_pct = EXCLUDED.allocated_pct, created_at = NOW();
        """,
        values,
    )
    conn.commit()
    cur.close()
    conn.close()


def delete_allocations(user_id: int):
    """
    Delete all allocation records from the database.
    TODO: Implement conditional deletion based on parameters.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM allocations WHERE user_id = %s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
