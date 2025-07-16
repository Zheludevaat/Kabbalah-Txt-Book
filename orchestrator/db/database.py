import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv('DATABASE_PATH', 'workspace/bookgen.db'))

_schema = """
CREATE TABLE IF NOT EXISTS steps(
    id TEXT,
    status TEXT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute(_schema)
    con.commit()
    con.close()

class DB:
    def __init__(self, db_path: Path = DB_PATH):
        init_db(db_path)
        self.db_path = db_path

    def log(self, step_id: str, status: str):
        con = sqlite3.connect(self.db_path)
        con.execute('INSERT INTO steps(id, status) VALUES (?, ?)', (step_id, status))
        con.commit()
        con.close()
