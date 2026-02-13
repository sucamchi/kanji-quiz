from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROGRESS_FILE = "progress.json"


def load_progress(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"cards": {}}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_progress(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def card_state(data: dict[str, Any], kanji: str) -> dict[str, Any]:
    cards = data.setdefault("cards", {})
    return cards.setdefault(
        kanji,
        {
            "repetitions": 0,
            "interval": 0,
            "ease_factor": 2.5,
            "due": "",
            "attempts": 0,
            "correct": 0,
        },
    )
