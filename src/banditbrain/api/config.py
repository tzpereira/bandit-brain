import os
import time

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection(retries=1, delay=2):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except psycopg2.OperationalError as e:
            print(f"DB connection failed (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(delay)
    raise Exception("Could not connect to the database after multiple attempts.")
