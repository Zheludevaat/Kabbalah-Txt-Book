import yaml
from pathlib import Path
from datetime import datetime
import shutil
import os
from typing import Optional

from .agents import (
    research_agent,
    instruction_agent,
    draft_agent,
    review_agent,
    rewrite_agent,
    formatter_agent,
    plagiarism_scan_agent,
)
from .agents.coordinator_agent import CoordinatorAgent

try:  # pragma: no cover - optional
    from prefect import flow, task
except Exception:  # pragma: no cover
    flow = task = None


def backup_workspace(
    workspace: Path,
    backup_dir: Optional[Path] = None,
    password: Optional[str] = None,
) -> Path:
    """Archive the workspace to a zip file and optionally encrypt it."""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    if backup_dir is None:
        backup_dir = workspace.parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive = backup_dir / f"{workspace.name}_{ts}.zip"
    if password:
        import pyzipper

        with pyzipper.AESZipFile(
            archive,
            'w',
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(password.encode())
            for root, _, files in os.walk(workspace):
                for file in files:
                    fp = Path(root) / file
                    zf.write(fp, fp.relative_to(workspace))
    else:
        shutil.make_archive(str(archive.with_suffix("")), 'zip', workspace)
    return archive


class PipelineRunner:
    def __init__(
        self,
        pipeline_file: Path = Path('pipeline/pipeline.yaml'),
        workspace: Path = Path('workspace'),
        backup_dir: Optional[Path] = None,
    ):
        self.pipeline_file = Path(pipeline_file)
        self.workspace = Path(workspace)
        env_backup = os.getenv('BACKUP_DIR')
        self.backup_dir = Path(env_backup) if backup_dir is None and env_backup else backup_dir
        self.password = os.getenv('BACKUP_PASSWORD')
        self.coordinator = CoordinatorAgent()
        settings_file = self.workspace / 'prebake' / 'global' / 'settings.json'
        if settings_file.exists():
            import json

            data = json.loads(settings_file.read_text())
        else:
            data = {}
        env_budget = os.getenv('TOKEN_BUDGET')
        self.token_budget = int(env_budget) if env_budget else int(
            data.get('token_budget_hard_cap', 0)
        )
        self.plagiarism_agent = plagiarism_scan_agent.PlagiarismScanAgent()

    def _load_pipeline(self) -> list[dict]:
        if not self.pipeline_file.exists():
            raise FileNotFoundError(f'{self.pipeline_file} missing')
        data = yaml.safe_load(self.pipeline_file.read_text())
        if not isinstance(data, dict) or 'steps' not in data:
            raise ValueError('pipeline must contain steps')
        return data['steps']

    def run(self):
        steps = self._load_pipeline()
        if flow is None:
            return self._run_sync(steps)
        return self._run_prefect(steps)

    def _run_sync(self, steps: list[dict]):
        manuscript_parts = []
        total_tokens = 0
        for step in steps:
            try:
                tokens = self._run_step(step, manuscript_parts)
            except Exception as e:
                print(f"Pipeline failed at {step['id']}: {e}", flush=True)
                return False
            if tokens:
                total_tokens += tokens
                if self.token_budget and total_tokens > self.token_budget:
                    print("Token budget exceeded", flush=True)
                    return False
        backup_workspace(self.workspace, self.backup_dir, self.password)
        print(f'Pipeline run complete. Tokens used: {total_tokens}', flush=True)
        return True

    def _run_step(self, step: dict, manuscript_parts: list[str]) -> int:
        agent = step['agent']
        prompt = Path(step['prompt'])
        step_dir = prompt.parent
        print(f"Running {step['id']} with {agent}...", flush=True)
        self.coordinator.start(step['id'])
        allowed = {
            'ResearchAgent',
            'InstructionAgent',
            'DraftAgent',
            'ReviewAgent',
            'RewriteAgent',
            'FormatterAgent',
        }
        if agent not in allowed:
            self.coordinator.end(step['id'], 'error')
            raise ValueError(f'Unknown agent: {agent}')
        tokens = 0
        try:
            if agent == 'ResearchAgent':
                notes = research_agent.fetch_research(step_dir.parent)
                (step_dir / 'research.txt').write_text('\n'.join(notes))
            elif agent == 'InstructionAgent':
                instruction_agent.create_brief(prompt)
            elif agent == 'DraftAgent':
                draft, tokens = draft_agent.write_draft(prompt)
                manuscript_parts.append(draft.read_text())
            elif agent == 'ReviewAgent':
                review_agent.review_draft(step_dir / 'draft.txt')
            elif agent == 'RewriteAgent':
                out = rewrite_agent.apply_fixes(step_dir / 'draft.txt', step_dir / 'review.txt')
                manuscript_parts[-1] = out.read_text()
                score = self.plagiarism_agent.run(''.join(manuscript_parts))
                (step_dir / 'plagiarism.txt').write_text(str(score))
                if score > 0.8:
                    out.write_text(out.read_text() + '\nRephrase needed.')
                    manuscript_parts[-1] = out.read_text()
            elif agent == 'FormatterAgent':
                manuscript = ''.join(manuscript_parts)
                formatter_agent.export(manuscript, self.workspace / 'output')
        except Exception as e:
            self.coordinator.end(step['id'], 'error')
            raise e
        else:
            self.coordinator.end(step['id'])
            print(f"Completed {step['id']}", flush=True)
            if tokens:
                print(f"TOKENS_USED={tokens}", flush=True)
            return tokens
    def _run_prefect(self, steps: list[dict]):
        @task
        def run_step(step, manuscript_parts):
            self._run_step(step, manuscript_parts)

        @flow
        def pipeline():
            parts = []
            for st in steps:
                run_step(st, parts)
            return True

        return pipeline()


def main():
    PipelineRunner().run()


if __name__ == '__main__':
    main()
