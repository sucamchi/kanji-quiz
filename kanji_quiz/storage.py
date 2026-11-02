"""Read and write the progress file."""
from __future__ import annotations

import json
from pathlib import Path

PROGRESS = "progress.json"


def load_progress(path: Path) -> dict:
    if not path.exists():
        return {"cards": {}, "history": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(path: Path, data: dict) -> None:
    # Write a temporary file and swap it in, so a Ctrl+C halfway through
    # a save cannot leave a half-written progress file behind.
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    temp.replace(path)
