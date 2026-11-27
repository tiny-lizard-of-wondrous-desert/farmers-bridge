"""Shared username cleanup for local and online player records."""

from __future__ import annotations

_ALLOWED_SYMBOLS = set(" _.-!?:;,'()[]{}+&#@%$=~`^\\/|*")
_HEART_TOKEN = "FARMERSBRIDGEHEARTTOKEN"


def clean_player_name(value: str) -> str:
    """Keep Unicode letters/digits, spaces, and common symbols such as ``:)`` and ``<3``."""
    value = str(value).replace("<3", _HEART_TOKEN)
    cleaned = "".join(
        character
        for character in value
        if character.isalnum() or character.isspace() or character in _ALLOWED_SYMBOLS
    )
    cleaned = cleaned.replace(_HEART_TOKEN, "<3")
    return " ".join(cleaned.split()).strip()
