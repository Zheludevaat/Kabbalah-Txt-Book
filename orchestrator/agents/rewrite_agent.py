from pathlib import Path


def apply_fixes(draft_path: Path, review_path: Path) -> Path:
    draft = draft_path.read_text()
    review = review_path.read_text()
    out = draft_path.parent / 'rewrite.txt'
    if review.strip() != 'OK':
        out.write_text(draft + '\n' + review)
    else:
        out.write_text(draft)
    return out
