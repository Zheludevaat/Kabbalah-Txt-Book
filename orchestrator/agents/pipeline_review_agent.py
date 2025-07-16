import yaml
from pathlib import Path


class PipelineReviewAgent:
    """Validate the pipeline YAML produced by PipelineBuilderAgent."""

    def __init__(self, pipeline_file: Path | str = Path("pipeline/pipeline.yaml")):
        self.pipeline_file = Path(pipeline_file)

    def run(self) -> dict:
        if not self.pipeline_file.exists():
            raise FileNotFoundError(f"{self.pipeline_file} missing")
        try:
            data = yaml.safe_load(self.pipeline_file.read_text())
        except yaml.YAMLError as e:
            raise ValueError("invalid pipeline.yaml") from e
        if not isinstance(data, dict) or "steps" not in data:
            raise ValueError("pipeline must contain steps list")
        if not isinstance(data["steps"], list):
            raise ValueError("steps must be a list")
        seen = set()
        for step in data["steps"]:
            if not isinstance(step, dict):
                raise ValueError("each step must be a mapping")
            step_id = step.get("id")
            agent = step.get("agent")
            prompt = step.get("prompt")
            if not step_id or not agent or not prompt:
                raise ValueError("step missing required fields")
            if step_id in seen:
                raise ValueError(f"duplicate step id {step_id}")
            seen.add(step_id)
            if not Path(prompt).exists():
                raise FileNotFoundError(f"prompt {prompt} missing")
        return data


if __name__ == "__main__":
    PipelineReviewAgent().run()
