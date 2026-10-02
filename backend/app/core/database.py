from contextlib import contextmanager
from psycopg import Connection
from psycopg.rows import dict_row
from app.core.config import settings

@contextmanager
def get_conn():
    conn = Connection.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
