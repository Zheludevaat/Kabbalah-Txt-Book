import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from pathlib import Path
from orchestrator.agents.prebake_agent import PrebakeAgent


def test_merge_chapter(tmp_path):
    plan = {
        'outline': [
            {
                'slug': 'c1',
                'title': 'C1',
                'parts': [
                    {'name': 'p1'},
                    {'name': 'p2'},
                    {'name': 'p3'},
                ]
            }
        ]
    }
    book_plan = tmp_path / 'book_plan.json'
    book_plan.write_text(json.dumps(plan))
    workspace = tmp_path / 'workspace'
    PrebakeAgent(book_plan, workspace).run()
    parts_dir = workspace / 'prebake' / 'chapters' / '01_c1' / 'parts'
    parts = sorted(parts_dir.iterdir())
    # Draft phase
    for p in parts:
        p.write_text(f"draft {p.name}\n")
        assert p.read_text().strip()
    # Merge and review
    merged = ''.join(p.read_text() for p in parts)
    assert merged.strip()
