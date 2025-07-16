import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from pathlib import Path
import yaml
import pytest
from orchestrator.agents.prebake_agent import (
    PrebakeAgent,
    split_part,
    est_tokens,
    OVERHEAD_TOKENS,
)


def test_prebake(tmp_path):
    plan = {
        'metadata': {
            'title': 'Book',
            'genre': 'fantasy',
            'target_audience': 'all',
            'language': 'en-US'
        },
        'output_preferences': {'chapter_size_words': 20000, 'token_budget_hard_cap': 16000},
        'outline': [
            {
                'slug': 'intro',
                'title': 'Intro',
                'parts': [{'name': 'p1', 'words': 20000}]
            }
        ],
        'style_guidelines': 'Use short sentences.',
        'characters': ['Alice']
    }
    book_plan = tmp_path / 'book_plan.json'
    book_plan.write_text(json.dumps(plan))
    workspace = tmp_path / 'workspace'
    PrebakeAgent(book_plan, workspace).run()
    chapter_dir = workspace / 'prebake' / 'chapters' / '01_intro'
    assert chapter_dir.exists()
    links = yaml.safe_load((workspace / 'prebake' / 'pipeline_links.yaml').read_text())
    assert len(links) == len(split_part(20000, 16000))
    for path in links.values():
        assert Path(path).exists()
    for words in split_part(20000, 16000):
        assert est_tokens(words) <= 16000 - OVERHEAD_TOKENS

    sample_prompt = Path(list(links.values())[0]).read_text()
    assert 'Use short sentences.' in sample_prompt
    assert 'Alice' in sample_prompt
    assert 'Book Title: Book' in sample_prompt


def test_prebake_invalid(tmp_path):
    bad = {'outline': [{'slug': 'c1', 'title': 'C1', 'parts': []}]}
    p = tmp_path / 'plan.json'
    p.write_text(json.dumps(bad))
    workspace = tmp_path / 'workspace'
    with pytest.raises(ValueError):
        PrebakeAgent(p, workspace).run()

    bad_words = {'outline': [{'slug': 'c2', 'title': 'C2', 'parts': [{'name': 'p', 'words': -5}]}]}
    p2 = tmp_path / 'plan2.json'
    p2.write_text(json.dumps(bad_words))
    with pytest.raises(ValueError):
        PrebakeAgent(p2, workspace).run()
