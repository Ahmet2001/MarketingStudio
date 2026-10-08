"""Three small text engines in one file: word count, most frequent words, and a Markdown report."""

import re
from collections import Counter

CAPABILITIES = [
    {"id": "summary.word_count", "function": "word_count", "description": "Counts the words in a text.",
     "network": False, "writes_external_state": False},
    {"id": "summary.top_words", "function": "top_words",
     "description": "The most frequent words (4 letters or more) in a text, most frequent first.",
     "network": False, "writes_external_state": False},
    {"id": "summary.report", "function": "report",
     "description": "A short Markdown report: title, word count and the most frequent words.",
     "network": False, "writes_external_state": False},
]


def word_count(text: str) -> int:
    return len(text.split())


def top_words(text: str, top: int = 5) -> list:
    words = re.findall(r"[^\W\d_]{4,}", text.lower())
    return [word for word, _ in Counter(words).most_common(top)]


def report(title: str, words: int, top: list) -> str:
    listing = ", ".join(top) if top else "(none)"
    return f"# {title}\n\n- Words: {words}\n- Most frequent: {listing}\n"
