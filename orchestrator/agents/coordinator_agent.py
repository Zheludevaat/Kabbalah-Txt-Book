from pathlib import Path
from ..db.database import DB

class CoordinatorAgent:
    """Record step progress in a local SQLite DB."""
    def __init__(self, db_path: Path | str = 'workspace/bookgen.db'):
        self.db = DB(Path(db_path))

    def start(self, step_id: str):
        self.db.log(step_id, 'start')

    def end(self, step_id: str, status: str = 'done'):
        self.db.log(step_id, status)
