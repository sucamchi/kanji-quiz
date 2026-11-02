"""Rebuild the kanji dataset from KanjiAPI's bulk download."""
from __future__ import annotations

import io
import json
import zipfile
from urllib.request import Request, urlopen

from .data_loader import DATASET, LEVELS

KANJIAPI_URL = "https://kanjiapi.dev/kanjiapi_full.zip"


def kanken_level(record: dict) -> str:
    """Guess a Kanken level from the school grade KanjiAPI gives.

    Kanken 10 to 5 line up with school grades 1 to 6. Grade 8 means
    secondary school, which roughly covers Kanken 4. Anything else on a
    JLPT list goes to 3, and the rest to 2 (not quizzed).
    """
    grade = record.get("grade")
    if grade in (1, 2, 3, 4, 5, 6):
        return str(11 - grade)
    if grade == 8:
        return "4"
    if record.get("jlpt"):
        return "3"
    return "2"


def clean_meanings(meanings: list[str]) -> list[str]:
    """Lowercase, squeeze spaces and drop duplicates, keeping order."""
    cleaned: list[str] = []
    for item in meanings:
        value = " ".join(item.split()).lower()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def write_kanken_dataset() -> int:
    request = Request(KANJIAPI_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; kanji-quiz-importer/1.0)"})
    with urlopen(request, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    payload = json.loads(archive.read("kanjiapi_full.json"))

    output = []
    for kanji, record in payload["kanjis"].items():
        level = kanken_level(record)
        meanings = clean_meanings(record.get("meanings") or [])
        if level in LEVELS and meanings:
            output.append(
                {"kanji": kanji, "level": level, "meanings": meanings})

    # Easiest level first: load_kanji() and the lesson order rely on this.
    output.sort(key=lambda item: (-int(item["level"]), item["kanji"]))
    DATASET.write_text(json.dumps(output, ensure_ascii=False, indent=4)
                       + "\n", encoding="utf-8")
    return len(output)
