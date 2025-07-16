from pathlib import Path


def export(manuscript: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / 'manuscript.txt'
    out.write_text(manuscript)
    return out
