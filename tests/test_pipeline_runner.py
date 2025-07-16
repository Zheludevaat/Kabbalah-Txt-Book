import json
from pathlib import Path
import yaml

from orchestrator.agents.prebake_agent import PrebakeAgent
from orchestrator import pipeline_builder
from orchestrator.pipeline_runner import PipelineRunner
import os
import pyzipper


def test_pipeline_runner(tmp_path):
    plan = {
        'metadata': {'title': 'Runner', 'genre': 'g', 'target_audience': 'ta', 'language': 'en-US'},
        'outline': [
            {'slug': 'c', 'title': 'C', 'parts': [{'name': 'p1'}]}
        ]
    }
    book_plan = tmp_path / 'plan.json'
    book_plan.write_text(json.dumps(plan))
    workspace = tmp_path / 'workspace'
    PrebakeAgent(book_plan, workspace).run()
    pipeline_builder.PIPELINE_LINKS_FILE = workspace / 'prebake' / 'pipeline_links.yaml'
    pipeline_builder.PIPELINE_FILE = tmp_path / 'pipeline' / 'pipeline.yaml'
    data = pipeline_builder.build_pipeline()
    step = data['steps'][0]
    # add review step
    data['steps'].append({
        'id': step['id'] + '_review',
        'agent': 'ReviewAgent',
        'prompt': step['prompt'],
        'depends_on': step['id']
    })
    Path(pipeline_builder.PIPELINE_FILE).write_text(yaml.safe_dump(data))
    backup_dir = tmp_path / 'backups'
    os.environ['BACKUP_DIR'] = str(backup_dir)
    os.environ['BACKUP_PASSWORD'] = 'secret'
    try:
        runner = PipelineRunner(pipeline_builder.PIPELINE_FILE, workspace)
        runner.run()
    finally:
        os.environ.pop('BACKUP_DIR')
        os.environ.pop('BACKUP_PASSWORD')
    step_dir = Path(step['prompt']).parent
    assert (step_dir / 'draft.txt').exists()
    assert (step_dir / 'review.txt').exists()
    zips = list(backup_dir.glob('workspace_*.zip'))
    assert len(zips) == 1
    with pyzipper.AESZipFile(zips[0]) as zf:
        zf.setpassword(b'secret')
        names = zf.namelist()
        assert any(name.endswith('metadata.json') for name in names)

