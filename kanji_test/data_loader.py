from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class KanjiEntry:
    kanji: str
    level: str
    meanings: tuple[str, ...]


def level_sort_value(level: str) -> tuple[int, str]:
    if level.isdigit():
        return (-int(level), level)
    return (999, level)


def load_kanji() -> list[KanjiEntry]:
    dataset = files("kanji_test.data").joinpath(
        "kanji_kanken.json").read_text(encoding="utf-8")
    raw = json.loads(dataset)

    entries = [
        KanjiEntry(
            kanji=item["kanji"],
            level=str(item["level"]),
            meanings=tuple(item["meanings"]),
        )
        for item in raw
    ]
    entries.sort(key=lambda entry: (
        level_sort_value(entry.level), entry.kanji))
    return entries
