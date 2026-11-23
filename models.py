import sqlite3
import os
import tempfile
from datetime import datetime
import config

DATABASE_PATH = config.DATABASE_PATH

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled."""
    db_path = config.DATABASE_PATH
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
    except sqlite3.OperationalError:
        # Fallback to /tmp if primary path cannot be opened (e.g. read-only filesystem on Vercel)
        fallback_path = os.path.join(tempfile.gettempdir(), "lablink.db")
        config.DATABASE_PATH = fallback_path
        conn = sqlite3.connect(fallback_path, timeout=30.0)

    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
