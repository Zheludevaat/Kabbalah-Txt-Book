"""Pipeline builder for the Book Generation app.

The builder consumes ``workspace/prebake/pipeline_links.yaml`` produced by
``PrebakeAgent``. For each entry it creates a pipeline step referencing a
prompt file.  Prompt text is generated from the prebake template using GPT‑4.1
when an API key is available. The model is then asked to review the generated
content for sanity.  The resulting prompt is stored under ``pipeline/`` and a
``pipeline.yaml`` describing the steps is written.

When no ``OPENAI_API_KEY`` is configured the GPT calls are skipped and the
original template text is used directly. This keeps tests deterministic while
allowing real runs to leverage GPT‑4.1 for richer prompts.
"""

import os
import yaml
from pathlib import Path

try:
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional
    openai = None

PIPELINE_LINKS_FILE = Path('workspace/prebake/pipeline_links.yaml')
PIPELINE_FILE = Path('pipeline/pipeline.yaml')
TEMPLATES_DIR = Path('templates')


def _call_gpt(prompt: str) -> str:
    """Send prompt to GPT-4.1 and return the response.

    If the ``openai`` module or API key is unavailable, the original prompt is
    returned so tests can run offline.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or openai is None:
        return prompt

    try:  # pragma: no cover - network
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model='gpt-4.1',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=4000,
        )
        return resp.choices[0].message['content']
    except Exception:
        return prompt


def _generate_prompt(template_path: Path, context: dict, extra: str = "") -> str:
    """Fill the template with context and ask GPT to refine it."""
    text = template_path.read_text()
    base = text.format(**context)
    combined = base
    if extra:
        combined += "\n" + extra
    draft = _call_gpt(combined)
    review_prompt = (
        "Review this prompt for errors and return the fixed version:\n" + draft
    )
    reviewed = _call_gpt(review_prompt)
    if reviewed.strip() == review_prompt:
        reviewed = draft
    return reviewed


def _load_links(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError("Invalid pipeline_links.yaml") from e
    if not isinstance(data, dict):
        raise ValueError("pipeline_links.yaml must map ids to paths or objects")
    return data


def _parse_entry(value) -> tuple[str, str]:
    """Return (agent, prompt_path) for a pipeline entry."""
    if isinstance(value, str):
        return "DraftAgent", value
    if isinstance(value, dict):
        agent = value.get("agent", "DraftAgent")
        prompt = value.get("prompt")
        if not prompt:
            raise ValueError("entry dict requires 'prompt' field")
        return agent, prompt
    raise ValueError("pipeline_links entries must be strings or dicts")


def build_pipeline():
    links = _load_links(PIPELINE_LINKS_FILE)

    steps = []
    previous_id = None
    seen_ids = set()

    for node_id, value in sorted(links.items()):
        if node_id in seen_ids:
            raise ValueError(f"duplicate node id {node_id}")
        agent, prompt_path = _parse_entry(value)
        prompt = Path(prompt_path)
        if not prompt.exists():
            raise FileNotFoundError(f"prompt {prompt} missing")

        # Generate final prompt text via GPT and store under pipeline dir
        out_dir = PIPELINE_FILE.parent / node_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_prompt = out_dir / 'prompt.txt'
        # gather chapter info if available
        chapter_dir = prompt.parent.parent
        meta_file = chapter_dir / 'metadata.json'
        chapter_title = ''
        if meta_file.exists():
            import json
            chapter_title = json.loads(meta_file.read_text()).get('title', '')
        outline_file = chapter_dir / 'outline.md'
        chapter_outline = outline_file.read_text() if outline_file.exists() else ''
        global_dir = PIPELINE_LINKS_FILE.parent.parent / 'global'
        meta_global = global_dir / 'metadata.json'
        settings_file = global_dir / 'settings.json'
        book_meta = {}
        settings = {}
        if meta_global.exists():
            import json
            book_meta = json.loads(meta_global.read_text())
        if settings_file.exists():
            import json
            settings = json.loads(settings_file.read_text())
        style_path = global_dir / 'style.md'
        chars_path = global_dir / 'characters.md'
        context = {
            "node_id": node_id,
            "agent": agent,
            "chapter_title": chapter_title,
            "chapter_outline": chapter_outline,
            "style_guidelines": style_path.read_text() if style_path.exists() else "",
            "characters": chars_path.read_text() if chars_path.exists() else "",
            "research_links": (chapter_dir / 'research_links.md').read_text()
            if (chapter_dir / 'research_links.md').exists() else "",
            "book_title": book_meta.get('title', ''),
            "genre": book_meta.get('genre', ''),
            "target_audience": book_meta.get('target_audience', ''),
            "language": book_meta.get('language', ''),
            "file_formats": ', '.join(settings.get('file_formats', [])),
            "manuscript_path": str(Path('workspace') / 'manuscript.txt'),
            "part_name": '',
        }

        base_name = agent[:-5] if agent.lower().endswith('agent') else agent
        template = TEMPLATES_DIR / f"{base_name.lower()}_agent_prompt.txt"
        if template.exists():
            out_prompt.write_text(_generate_prompt(template, context, prompt.read_text()))
        else:
            out_prompt.write_text(_generate_prompt(prompt, context))

        step = {
            "id": node_id,
            "agent": agent,
            "prompt": str(out_prompt),
        }
        if previous_id:
            step["depends_on"] = previous_id
        steps.append(step)
        previous_id = node_id
        seen_ids.add(node_id)

    pipeline = {"steps": steps}
    PIPELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_FILE.write_text(yaml.safe_dump(pipeline))
    return pipeline

if __name__ == '__main__':
    build_pipeline()
