import os
import requests
from pathlib import Path

def _browsing_enabled() -> bool:
    """Return whether HTTP requests are allowed."""
    flag = os.getenv("BROWSING_ENABLED", "1").lower()
    return flag not in ("0", "false", "no")


def fetch_research(chapter_dir: Path, browsing: bool | None = None):
    """Fetch research pages listed in research_links.md.
    If browsing is disabled or a request fails, fall back to the file contents."""
    links_file = chapter_dir / 'research_links.md'
    if not links_file.exists():
        return []
    urls = [l.strip() for l in links_file.read_text().splitlines() if l.strip()]
    results = []
    if browsing is None:
        browsing = _browsing_enabled()
    if browsing:
        for url in urls:
            try:
                r = requests.get(url, timeout=5)
                results.append(r.text[:200])
            except Exception:
                pass
    if not results:
        results.append(links_file.read_text())
    return results
