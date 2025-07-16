from pathlib import Path


def write_draft(prompt_path: Path, instruction_text: str | None = None) -> tuple[Path, int]:
    """Write draft text and return output path and estimated tokens."""
    text = prompt_path.read_text()
    if instruction_text:
        text = instruction_text + "\n" + text
    out = prompt_path.parent / "draft.txt"
    out.write_text(text)
    tokens = int(len(text.split()) * 1.3)
    return out, tokens
