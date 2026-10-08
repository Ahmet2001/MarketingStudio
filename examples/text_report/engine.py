"""Text analysis engines in one file: keywords from a text file, and a Markdown report."""

import re
from collections import Counter
from pathlib import Path

CAPABILITIES = [
    {
        "id": "text.keywords",
        "function": "keywords",
        "description": "Finds the most frequent words (longer than 3 letters) in a text file.",
        "network": False,
        "writes_external_state": False,
    },
    {
        "id": "text.report",
        "function": "report",
        "description": "Writes a Markdown report file with the title, keywords and a short summary line.",
        "network": False,
        "writes_external_state": False,
    },
]


def keywords(source: Path, top: int = 5) -> list:
    words = re.findall(r"[^\W\d_]{4,}", source.read_text(encoding="utf-8").lower())
    return [word for word, _ in Counter(words).most_common(top)]


def report(title: str, keywords: list, summary: str, out: Path) -> Path:
    body = f"# {title}\n\n{summary}\n\n## Keywords\n" + "\n".join(f"- {k}" for k in keywords) + "\n"
    out.write_text(body, encoding="utf-8")
    return out
