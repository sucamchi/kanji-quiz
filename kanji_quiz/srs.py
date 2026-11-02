"""WaniKani-style spaced repetition: stages, review times and unlocking."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from .data_loader import LEVELS, KanjiEntry

STAGE_NAMES = (
    "", "Apprentice 1", "Apprentice 2", "Apprentice 3", "Apprentice 4",
    "Guru 1", "Guru 2", "Master", "Enlightened", "Burned")
GURU = 5
BURNED = 9

# Hours until the next review, per stage. These are WaniKani's numbers:
# 23 and 47 rather than 24 and 48 so that reviewing at the same time every
# day still finds the item due, and likewise one hour off a week or month.
INTERVALS = {1: 4, 2: 8, 3: 23, 4: 47, 5: 167, 6: 335, 7: 719, 8: 2879}

# WaniKani opens the next level once 90% of the current one is Guru or up.
UNLOCK_SHARE = 0.9


def stage_group(stage: int) -> str:
    """Stage name without its number, e.g. "Apprentice" for stages 1-4."""
    return STAGE_NAMES[stage].split()[0]


def schedule(card: dict, now: datetime) -> None:
    if card["stage"] == BURNED:
        card["due"] = None
        return
    due = now + timedelta(hours=INTERVALS[card["stage"]])
    # Rounded down to the hour, like WaniKani, so reviews arrive in batches.
    card["due"] = due.replace(minute=0, second=0, microsecond=0).isoformat()


def new_card(now: datetime) -> dict:
    card: dict = {"stage": 1}
    schedule(card, now)
    return card


def is_due(card: dict, now: datetime) -> bool:
    if card["due"] is None:
        return False
    return datetime.fromisoformat(card["due"]) <= now


def apply_review(card: dict, misses: int, now: datetime) -> None:
    """Move a card up one stage, or down if it was missed this session."""
    if misses == 0:
        card["stage"] += 1
    else:
        # WaniKani's penalty: one stage per two misses (rounded up), and
        # double that once the card has reached Guru.
        penalty = 2 if card["stage"] >= GURU else 1
        drop = math.ceil(misses / 2) * penalty
        card["stage"] = max(1, card["stage"] - drop)
    schedule(card, now)


def guru_needed(entries: list[KanjiEntry], cards: dict, level: str) -> int:
    """How many more kanji in this level must reach Guru to unlock the next."""
    level_kanji = [entry.kanji for entry in entries if entry.level == level]
    at_guru = 0
    for kanji in level_kanji:
        if kanji in cards and cards[kanji]["stage"] >= GURU:
            at_guru += 1
    return max(0, math.ceil(UNLOCK_SHARE * len(level_kanji)) - at_guru)


def unlocked_levels(entries: list[KanjiEntry], cards: dict) -> list[str]:
    unlocked = []
    for level in LEVELS:
        unlocked.append(level)
        if guru_needed(entries, cards, level) > 0:
            break
    return unlocked


def available_lessons(
        entries: list[KanjiEntry], cards: dict) -> list[KanjiEntry]:
    """Kanji in unlocked levels that have not been learned yet, in order."""
    unlocked = unlocked_levels(entries, cards)
    lessons = []
    for entry in entries:
        if entry.level in unlocked and entry.kanji not in cards:
            lessons.append(entry)
    return lessons
