from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile
from urllib.request import Request, urlopen

KANJIAPI_BULK_URL = "https://kanjiapi.dev/kanjiapi_full.zip"
LEVELS = ("10", "9", "8", "7", "6", "5", "4", "3")


def _fetch_bytes(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; kanji-test-importer/1.0)",
            "Accept": "application/json, application/zip, */*",
        },
    )
    with urlopen(request, timeout=120) as response:
        return response.read()


def _normalize_meanings(meanings: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in meanings:
        value = " ".join(item.strip().split()).lower()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _map_to_kanken_level(record: dict[str, object]) -> str:
    grade = record.get("grade")
    jlpt = record.get("jlpt")

    if grade in (1, 2, 3, 4, 5, 6):
        return str(11 - int(grade))

    if grade == 8:
        return "4"

    if jlpt in (1, 2, 3, 4, 5):
        return "3"
    return "2"


def _load_kanjiapi_bulk_records() -> dict[str, dict[str, object]]:
    raw = _fetch_bytes(KANJIAPI_BULK_URL)
    archive = zipfile.ZipFile(io.BytesIO(raw))
    payload = json.loads(archive.read("kanjiapi_full.json").decode("utf-8"))
    kanjis = payload.get("kanjis", {})
    if not isinstance(kanjis, dict):
        raise ValueError("Invalid KanjiAPI bulk format: missing 'kanjis' map")
    return kanjis


def scrape_kanken_levels(levels: tuple[str, ...] = LEVELS) -> list[dict[str, object]]:
    allowed = set(levels)
    records = _load_kanjiapi_bulk_records()

    output: list[dict[str, object]] = []
    for kanji, record in records.items():
        if not isinstance(record, dict):
            continue

        mapped_level = _map_to_kanken_level(record)
        if mapped_level not in allowed:
            continue

        meanings_raw = record.get("meanings")
        if not isinstance(meanings_raw, list):
            continue

        meanings = _normalize_meanings([str(item) for item in meanings_raw])
        if not meanings:
            continue

        output.append(
            {
                "kanji": kanji,
                "level": mapped_level,
                "meanings": meanings,
            }
        )

    output.sort(
        key=lambda item: (-int(str(item["level"])), str(item["kanji"])))
    return output


def write_kanken_dataset(output_path: Path, levels: tuple[str, ...] = LEVELS) -> int:
    data = scrape_kanken_levels(levels=levels)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    return len(data)
