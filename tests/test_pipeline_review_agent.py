import json
from pathlib import Path
import pytest
import yaml

from orchestrator.agents.prebake_agent import PrebakeAgent
from orchestrator import pipeline_builder
from orchestrator.agents.pipeline_review_agent import PipelineReviewAgent


def _build_pipeline(tmp_path: Path) -> Path:
    plan = {
        "outline": [
            {"slug": "s1", "title": "S1", "parts": [{"name": "p1"}]}]
    }
    book_plan = tmp_path / "book_plan.json"
    book_plan.write_text(json.dumps(plan))
    workspace = tmp_path / "workspace"
    PrebakeAgent(book_plan, workspace).run()
    pipeline_builder.PIPELINE_LINKS_FILE = workspace / "prebake" / "pipeline_links.yaml"
    pipeline_builder.PIPELINE_FILE = tmp_path / "pipeline" / "pipeline.yaml"
    pipeline_builder.build_pipeline()
    return pipeline_builder.PIPELINE_FILE


def test_pipeline_review_valid(tmp_path):
    pipeline_file = _build_pipeline(tmp_path)
    PipelineReviewAgent(pipeline_file).run()


def test_pipeline_review_missing_prompt(tmp_path):
    pipeline_file = _build_pipeline(tmp_path)
    data = yaml.safe_load(Path(pipeline_file).read_text())
    # remove prompt file
    step = data["steps"][0]
    Path(step["prompt"]).unlink()
    Path(pipeline_file).write_text(yaml.safe_dump(data))
    with pytest.raises(FileNotFoundError):
        PipelineReviewAgent(pipeline_file).run()
