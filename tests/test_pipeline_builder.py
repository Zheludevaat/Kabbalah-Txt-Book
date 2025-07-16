import json
from pathlib import Path
import yaml
import pytest
from orchestrator.agents.prebake_agent import PrebakeAgent
from orchestrator import pipeline_builder


def test_pipeline_builder(tmp_path):
    plan = {
        'metadata': {'title': 'T', 'genre': 'g', 'target_audience': 'ta', 'language': 'en-US'},
        'outline': [
            {
                'slug': 's1',
                'title': 'S1',
                'parts': [{'name': 'p1'}, {'name': 'p2'}]
            }
        ]
    }
    book_plan = tmp_path / 'book_plan.json'
    book_plan.write_text(json.dumps(plan))
    workspace = tmp_path / 'workspace'
    PrebakeAgent(book_plan, workspace).run()
    pipeline_builder.PIPELINE_LINKS_FILE = workspace / 'prebake' / 'pipeline_links.yaml'
    pipeline_builder.PIPELINE_FILE = tmp_path / 'pipeline' / 'pipeline.yaml'
    pipeline = pipeline_builder.build_pipeline()
    assert pipeline_builder.PIPELINE_FILE.exists()
    data = yaml.safe_load(pipeline_builder.PIPELINE_FILE.read_text())
    steps = data['steps']
    assert len(steps) == len(pipeline['steps'])
    prev = None
    for step in steps:
        assert 'agent' in step and step['agent'] == 'DraftAgent'
        path = Path(step['prompt'])
        assert path.exists()
        text = path.read_text()
        assert 'DraftAgent Prompt Template' in text
        assert 'Write approximately' in text
        assert 'Book Title' in text
        if prev:
            assert step['depends_on'] == prev
        prev = step['id']


def test_pipeline_builder_custom_agent(tmp_path):
    links = {
        'chapter_01_part_01': {
            'prompt': str(tmp_path / 'p.txt'),
            'agent': 'ResearchAgent'
        }
    }
    (tmp_path / 'p.txt').write_text('hi')
    pipeline_builder.PIPELINE_LINKS_FILE = tmp_path / 'links.yaml'
    pipeline_builder.PIPELINE_FILE = tmp_path / 'pipeline.yaml'
    pipeline_builder.PIPELINE_LINKS_FILE.write_text(yaml.safe_dump(links))
    pipeline = pipeline_builder.build_pipeline()
    step = pipeline['steps'][0]
    assert step['agent'] == 'ResearchAgent'
    generated = Path(step['prompt'])
    assert generated.exists()
    text = generated.read_text()
    assert 'hi' in text
    assert '# ResearchAgent Prompt Template' in text
    assert generated != tmp_path / 'p.txt'

def test_pipeline_builder_invalid_yaml(tmp_path):
    bad = tmp_path / "links.yaml"
    bad.write_text(":\n- foo")
    pipeline_builder.PIPELINE_LINKS_FILE = bad
    pipeline_builder.PIPELINE_FILE = tmp_path / "p.yaml"
    with pytest.raises(ValueError):
        pipeline_builder.build_pipeline()


def test_pipeline_builder_missing_prompt(tmp_path):
    links = {"chapter_01_part_01": str(tmp_path / "missing.txt")}
    pipeline_builder.PIPELINE_LINKS_FILE = tmp_path / "links.yaml"
    pipeline_builder.PIPELINE_FILE = tmp_path / "p.yaml"
    pipeline_builder.PIPELINE_LINKS_FILE.write_text(yaml.safe_dump(links))
    with pytest.raises(FileNotFoundError):
        pipeline_builder.build_pipeline()

