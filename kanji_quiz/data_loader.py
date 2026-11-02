"""Load the bundled kanji dataset."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATASET = Path(__file__).with_name("data") / "kanji_kanken.json"

# Kanken levels this quiz covers, easiest (10) first. Lessons unlock in
# this order.
LEVELS = ("10", "9", "8", "7", "6", "5", "4", "3")


@dataclass(frozen=True)
class KanjiEntry:
    kanji: str
    level: str
    meanings: tuple[str, ...]


def load_kanji() -> list[KanjiEntry]:
    """Every kanji, easiest level first.

    The order comes from the file itself: importer.py writes it sorted.
    """
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    entries = []
    for item in raw:
        entries.append(KanjiEntry(
            item["kanji"], item["level"], tuple(item["meanings"])))
    return entries
