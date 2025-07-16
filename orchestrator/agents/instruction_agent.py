from pathlib import Path


def create_brief(prompt_path: Path, research_notes: list[str] | None = None) -> Path:
    """Return a brief text file based on the prompt and research."""
    text = prompt_path.read_text()
    notes = "\n".join(research_notes or [])
    out = prompt_path.parent / "instruction.txt"
    out.write_text(f"{text}\n{notes}")
    return out
