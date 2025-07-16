from pathlib import Path


def review_draft(draft_path: Path) -> Path:
    text = draft_path.read_text()
    issues = []
    if not text.strip():
        issues.append('empty draft')
    out = draft_path.parent / 'review.txt'
    if issues:
        out.write_text('\n'.join(issues))
    else:
        out.write_text('OK')
    return out
