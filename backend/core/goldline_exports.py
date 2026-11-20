"""Goldline (v4.1.1-goldline.5): exports for read-only users leave out the libraries' internal identifiers."""

import re

_PREFIX = re.compile(r"\[urn:[^\]]*\]\s*")


def strip_library_identifiers(entry: dict) -> dict:
    """The row without the "urn" column, and without "[urn:...]" prefixes in the answers cell."""
    out = {k: v for k, v in entry.items() if k != "urn"}
    if isinstance(out.get("answers"), str):
        out["answers"] = _PREFIX.sub("", out["answers"])
    return out
