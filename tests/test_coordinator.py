import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator.agents.coordinator_agent import CoordinatorAgent
import sqlite3


def test_coordinator_records(tmp_path):
    db_path = tmp_path / 'db.sqlite'
    agent = CoordinatorAgent(db_path)
    agent.start('step1')
    agent.end('step1', 'done')
    con = sqlite3.connect(db_path)
    rows = list(con.execute('SELECT status FROM steps WHERE id=? ORDER BY rowid DESC LIMIT 1', ('step1',)))
    con.close()
    assert rows[0][0] == 'done'
