class PlagiarismScanAgent:
    """Perform a simple plagiarism check using text similarity."""

    def __init__(self, references: list[str] | None = None) -> None:
        self.references = references or []

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a, b).ratio()

    def run(self, manuscript: str) -> float:
        """Return the highest similarity score against reference texts."""
        if not self.references:
            return 0.0
        scores = [self._similarity(manuscript, ref) for ref in self.references]
        return max(scores, default=0.0)
