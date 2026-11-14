"""The language of a language tag."""

from __future__ import annotations


def language_of(tag: str) -> str:
    """Return the language of a language tag: `fr` for `fr`, `fr-FR` or `fr_FR`."""
    return tag.replace("_", "-").partition("-")[0].lower()
