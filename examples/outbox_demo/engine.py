"""A stand-in for "send something to the outside world": it appends a message to a local outbox file.

It is declared as writing external state, so the factory forces approval on any step that uses it.
Nothing leaves the machine; the file is what you check to see whether the step ran.
"""

from pathlib import Path

CAPABILITIES = [
    {
        "id": "outbox.send",
        "function": "send",
        "description": "Appends a message for a recipient to the outbox file (a stand-in for sending it).",
        "network": True,
        "writes_external_state": True,
    },
]


def send(to: str, message: str) -> str:
    outbox = Path("outbox.txt")  # python engines run in their own step folder
    with outbox.open("a", encoding="utf-8") as handle:
        handle.write(f"To: {to}\n{message}\n---\n")
    return f"queued for {to} ({len(message)} characters)"
