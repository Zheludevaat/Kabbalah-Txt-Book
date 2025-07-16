import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
import re
import os

OVERHEAD_TOKENS = 512
TEMPLATES_DIR = Path('templates')

_slug_re = re.compile(r"[^a-zA-Z0-9_-]+")


def slugify(value: str) -> str:
    return _slug_re.sub("_", value).strip("_").lower()


def est_tokens(words: int) -> int:
    return int(words * 1.3)


def split_part(words: int, max_output_tokens: int):
    """Recursively split word counts so each estimated token
    count stays within limit."""
    if est_tokens(words) <= max_output_tokens - OVERHEAD_TOKENS:
        return [words]
    half = words // 2
    return split_part(half, max_output_tokens) + split_part(words - half, max_output_tokens)


@dataclass
class Part:
    name: str
    words: int = 0
    media_assets: list[str] = field(default_factory=list)


@dataclass
class Chapter:
    slug: str
    title: str
    parts: list[Part]
    research_links: list[str] = field(default_factory=list)
    media_assets: list[str] = field(default_factory=list)


class PrebakeAgent:
    def __init__(self, book_plan_path: Path, workspace: Path, save_api_key: bool | None = None):
        self.book_plan_path = book_plan_path
        self.workspace = workspace
        self.prebake_dir = workspace / 'prebake'
        self.chapters_dir = self.prebake_dir / 'chapters'
        self.global_dir = self.prebake_dir / 'global'
        self.settings = {}
        self.style_guidelines = ""
        self.characters_text = ""
        self.book_meta = {}
        self.book_title = ""
        self.genre = ""
        self.target_audience = ""
        self.language = ""
        if save_api_key is None:
            flag = os.getenv('SAVE_API_KEY')
            if flag is None:
                save_api_key = True
            else:
                save_api_key = flag.lower() not in ('0', 'false', 'no')
        self.save_api_key = save_api_key

    def _validate_plan(self, plan: dict) -> None:
        if not isinstance(plan, dict):
            raise ValueError("book_plan must be an object")
        outline = plan.get("outline")
        if not isinstance(outline, list) or not outline:
            raise ValueError("book_plan outline must be a non-empty list")
        for chapter in outline:
            if not isinstance(chapter, dict):
                raise ValueError("outline entries must be objects")
            if not chapter.get("slug") or not chapter.get("title"):
                raise ValueError("each chapter requires slug and title")
            parts = chapter.get("parts")
            if not isinstance(parts, list) or not parts:
                raise ValueError(f"chapter {chapter.get('slug')} must have parts list")
            for part in parts:
                if not isinstance(part, dict) or not part.get("name"):
                    raise ValueError("each part must be an object with a name")
                if "words" in part:
                    if not isinstance(part["words"], int) or part["words"] <= 0:
                        raise ValueError("part words must be a positive integer")

    def run(self):
        plan = json.loads(self.book_plan_path.read_text())
        self._validate_plan(plan)
        self.prebake_dir.mkdir(parents=True, exist_ok=True)
        self.settings = self._write_global(plan)
        links = {}
        for idx, chap_data in enumerate(plan.get('outline', []), start=1):
            chapter = Chapter(
                slug=chap_data['slug'],
                title=chap_data['title'],
                parts=[
                    Part(
                        name=p['name'],
                        words=p.get('words', self.settings['words_per_part']),
                        media_assets=p.get('media_assets', []),
                    )
                    for p in chap_data.get('parts', [])
                ],
                research_links=chap_data.get('research_links', []),
                media_assets=chap_data.get('media_assets', []),
            )
            links.update(self._process_chapter(idx, chapter))
        (self.prebake_dir / 'pipeline_links.yaml').write_text(yaml.safe_dump(links))

    def _write_global(self, plan: dict):
        self.global_dir.mkdir(parents=True, exist_ok=True)
        import os
        prefs = plan.get('output_preferences', {})
        default_settings = {
            'words_per_chapter': int(os.getenv('WORDS_PER_CHAPTER', prefs.get('chapter_size_words', 4000))),
            'words_per_part': int(os.getenv('WORDS_PER_PART', 1500)),
            'max_output_tokens': int(os.getenv('MAX_OUTPUT_TOKENS', prefs.get('token_budget_hard_cap', 16000))),
            'model': os.getenv('MODEL', 'gpt-4.1'),
        }
        default_settings.update(prefs)
        (self.global_dir / 'settings.json').write_text(json.dumps(default_settings, indent=2))
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and self.save_api_key:
            (self.global_dir / 'api_key.txt').write_text(api_key)
        self.style_guidelines = plan.get('style_guidelines', '# Style Guide\n')
        self.characters_text = '\n'.join(plan.get('characters', []))
        self.book_meta = plan.get('metadata', {})
        self.book_title = self.book_meta.get('title', '')
        self.genre = self.book_meta.get('genre', '')
        self.target_audience = self.book_meta.get('target_audience', '')
        self.language = self.book_meta.get('language', '')
        (self.global_dir / 'style.md').write_text(self.style_guidelines)
        (self.global_dir / 'characters.md').write_text(self.characters_text)
        (self.global_dir / 'metadata.json').write_text(
            json.dumps(self.book_meta, indent=2)
        )
        return default_settings

    def _safe_link(self, src: Path, dst: Path):
        try:
            dst.symlink_to(src.resolve())
        except Exception:
            import shutil
            shutil.copy2(src, dst)

    def _process_chapter(self, index: int, chapter: Chapter):
        safe_slug = slugify(chapter.slug)
        slug_dir = self.chapters_dir / f"{index:02d}_{safe_slug}"
        parts_dir = slug_dir / 'parts'
        media_dir = slug_dir / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        parts_dir.mkdir(parents=True, exist_ok=True)
        (slug_dir / 'metadata.json').write_text(json.dumps({'title': chapter.title}, indent=2))
        outline_lines = "\n".join(f"- {p.name}" for p in chapter.parts)
        (slug_dir / 'outline.md').write_text(f"# {chapter.title}\n{outline_lines}\n")
        (slug_dir / 'research_links.md').write_text('\n'.join(chapter.research_links))

        # copy chapter-level media assets
        for asset in chapter.media_assets:
            src = Path(asset)
            if src.exists():
                dst = media_dir / src.name
                if not dst.exists():
                    self._safe_link(src, dst)

        links = {}
        p_idx = 1
        for part in chapter.parts:
            segments = split_part(part.words, self.settings['max_output_tokens'])
            for words in segments:
                part_file = parts_dir / f"P{p_idx:02d}_prompt.txt"
                node_id = f"chapter_{index:02d}_part_{p_idx:02d}"
                template = TEMPLATES_DIR / 'draft_agent_prompt.txt'
                text = template.read_text().format(
                    chapter_title=chapter.title,
                    node_id=node_id,
                    style_guidelines=self.style_guidelines,
                    characters=self.characters_text,
                    research_links="\n".join(chapter.research_links),
                    book_title=self.book_title,
                    genre=self.genre,
                    target_audience=self.target_audience,
                    language=self.language,
                    chapter_outline=outline_lines,
                    part_name=part.name,
                )
                text += (
                    f"\nWrite approximately {words} words for the section titled '{part.name}'.\n"
                )
                part_file.write_text(text)
                links[node_id] = str(part_file)
                p_idx += 1
            # copy part-level media
            for asset in part.media_assets:
                src = Path(asset)
                if src.exists():
                    dst = media_dir / src.name
                    if not dst.exists():
                        self._safe_link(src, dst)
        return links


if __name__ == '__main__':
    PrebakeAgent(Path('book_plan.json'), Path('workspace')).run()
