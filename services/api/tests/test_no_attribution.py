"""Rule 25: no AI assistant or code-generation tool is credited anywhere in the repository.

The test reads every text file git tracks and fails on an attribution footer or credit line. It
looks for the footers such tools add, not for the word itself: instruction files for a tool are
allowed as pointers to the rule book (rule 24). Commit messages are not files; they are checked in
review.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

FOOTERS = (
    re.compile(r"Co-Authored-By:\s*(Claude|Gemini|ChatGPT|GPT|Copilot|Codex)", re.I),
    re.compile(r"Generated with \[?(Claude|Gemini|ChatGPT|Copilot|Codex)", re.I),
    re.compile(r"noreply@anthropic\.com", re.I),
    re.compile(r"claude\.com/claude-code", re.I),
)
TEXT = {".md", ".py", ".ts", ".tsx", ".json", ".toml", ".yml", ".yaml", ".txt", ".css", ".mjs"}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"],  # noqa: S607 - fixed argv, no input
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:  # not a git checkout (an exported archive)
        return [p for p in ROOT.rglob("*") if p.suffix in TEXT and ".venv" not in p.parts]
    return [ROOT / line for line in out.stdout.splitlines() if (ROOT / line).suffix in TEXT]


def test_no_tracked_file_carries_an_assistant_attribution():
    this_file = Path(__file__).resolve()
    hits = []
    for path in tracked_files():
        if path.resolve() == this_file or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FOOTERS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
    assert not hits, hits
