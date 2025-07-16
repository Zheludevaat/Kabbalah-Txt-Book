import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator.agents.plagiarism_scan_agent import PlagiarismScanAgent


def test_similarity_score():
    text = "hello world"
    agent = PlagiarismScanAgent(["hello world", "different text"])
    assert agent.run(text) > 0.9


def test_no_references():
    agent = PlagiarismScanAgent()
    assert agent.run("anything") == 0.0
