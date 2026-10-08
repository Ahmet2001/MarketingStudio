"""An engine that needs a package that is not in the standard library (humanize)."""

CAPABILITIES = [
    {
        "id": "fmt.size",
        "function": "size",
        "description": "Writes a byte count in human units, for example 1.5 MB.",
        "network": False,
        "writes_external_state": False,
        "packages": ["humanize"],
    },
]


def size(byte_count: int) -> str:
    import humanize  # imported when the step runs, so the engine can still be read without it installed

    return humanize.naturalsize(byte_count)
