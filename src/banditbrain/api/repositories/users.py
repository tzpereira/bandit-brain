from banditbrain.api.config import get_db_connection
from banditbrain.api.models import User


def get_user_by_email(email: str) -> User | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password, created_at, is_demo FROM users WHERE email = %s;", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"id": row[0], "email": row[1], "password": row[2], "created_at": row[3], "is_demo": row[4]}
    return None


def get_user_by_id(user_id: int) -> User | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password, created_at, is_demo FROM users WHERE id = %s;", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"id": row[0], "email": row[1], "password": row[2], "created_at": row[3], "is_demo": row[4]}
    return None


def create_user(email: str, password: str) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id;", (email, password))
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return user_id
