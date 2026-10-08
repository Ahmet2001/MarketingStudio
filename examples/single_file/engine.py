"""A whole engine in one file: the metadata below plus the functions are everything."""

from pathlib import Path
from typing import Literal

CAPABILITIES = [
    {
        "id": "demo.word_count",
        "function": "word_count",
        "description": "Counts the words in a text file.",
        "network": False,
        "writes_external_state": False,
    },
    {
        "id": "demo.headline",
        "function": "headline",
        "description": "Writes a headline that mentions how long the text is.",
        "network": False,
        "writes_external_state": False,
    },
]


def word_count(source: Path) -> int:
    return len(source.read_text(encoding="utf-8").split())


def headline(text: str, words: int, style: Literal["plain", "loud"] = "plain") -> str:
    line = f"{text} ({words} words)"
    return line.upper() + "!" if style == "loud" else line
