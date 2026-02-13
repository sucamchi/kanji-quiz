from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class CardState:
    repetitions: int = 0
    interval: int = 0
    ease_factor: float = 2.5
    due: str = ""


def is_due(due_iso: str, today: date | None = None) -> bool:
    if not due_iso:
        return True
    now = today or date.today()
    return date.fromisoformat(due_iso) <= now


def schedule_next(state: CardState, quality: int, today: date | None = None) -> CardState:
    now = today or date.today()

    clamped = max(0, min(5, quality))
    ease = state.ease_factor + \
        (0.1 - (5 - clamped) * (0.08 + (5 - clamped) * 0.02))
    ease = max(1.3, ease)

    if clamped < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = max(1, round(state.interval * ease))

    return CardState(
        repetitions=repetitions,
        interval=interval,
        ease_factor=ease,
        due=(now + timedelta(days=interval)).isoformat(),
    )
