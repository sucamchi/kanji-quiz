"""Command-line entry point: lessons, reviews and stats."""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from . import srs
from .answers import is_correct
from .data_loader import DATASET, LEVELS, KanjiEntry, load_kanji
from .importer import write_kanken_dataset
from .storage import PROGRESS, load_progress, save_progress

LESSON_BATCH = 5


def ask_until_right(
        entries: list[KanjiEntry]) -> Iterator[tuple[KanjiEntry, int]]:
    """Quiz each kanji in random order until every one has been answered.

    A wrong answer sends the kanji back into the queue. Each time a kanji
    is finally answered right, this yields it with its number of misses.
    """
    queue = list(entries)
    random.shuffle(queue)
    misses: dict[str, int] = {}
    while queue:
        entry = queue.pop(0)
        print(f"\n[{len(queue) + 1} left]  {entry.kanji}")
        meanings = ", ".join(entry.meanings)
        if is_correct(input("Meaning: "), entry.meanings):
            print(f"Correct: {meanings}")
            yield entry, misses.get(entry.kanji, 0)
        else:
            misses[entry.kanji] = misses.get(entry.kanji, 0) + 1
            print(f"Wrong. Accepted: {meanings}")
            # Put it back a few places on, not straight away.
            spot = random.randint(min(3, len(queue)), len(queue))
            queue.insert(spot, entry)


def cmd_lessons(args: argparse.Namespace) -> None:
    path = Path(args.progress)
    progress = load_progress(path)
    cards = progress["cards"]
    batch = srs.available_lessons(load_kanji(), cards)[:args.count]
    if not batch:
        print("No lessons available. Get more kanji to Guru to unlock the"
              " next level.")
        return

    for number, entry in enumerate(batch, start=1):
        print(f"\nLesson {number}/{len(batch)}  (Kanken {entry.level})")
        print(f"  {entry.kanji}  =  {', '.join(entry.meanings)}")
        input("Press Enter to continue...")

    print("\nNow a quick quiz on these. Misses here do not count.")
    for entry, _ in ask_until_right(batch):
        cards[entry.kanji] = srs.new_card(datetime.now())
        save_progress(path, progress)
    print(f"\nLearned {len(batch)} kanji. First review in 4 hours.")


def cmd_review(args: argparse.Namespace) -> None:
    path = Path(args.progress)
    progress = load_progress(path)
    cards = progress["cards"]
    now = datetime.now()
    due = []
    for entry in load_kanji():
        if entry.kanji in cards and srs.is_due(cards[entry.kanji], now):
            due.append(entry)
    if not due:
        print("No reviews due right now.")
        return

    first_try = 0
    for entry, misses in ask_until_right(due):
        card = cards[entry.kanji]
        before = srs.STAGE_NAMES[card["stage"]]
        srs.apply_review(card, misses, datetime.now())
        print(f"  {before} -> {srs.STAGE_NAMES[card['stage']]}")

        day = now.date().isoformat()
        levels = progress["history"].setdefault(day, {})
        record = levels.setdefault(entry.level, {"questions": 0, "correct": 0})
        record["questions"] += 1
        if misses == 0:
            record["correct"] += 1
            first_try += 1
        # Saved after every kanji, so quitting halfway keeps what was done.
        save_progress(path, progress)

    print(f"\nReviewed {len(due)} kanji, {first_try} right first time"
          f" ({first_try / len(due):.0%}).")


def cmd_stats(args: argparse.Namespace) -> None:
    progress = load_progress(Path(args.progress))
    cards = progress["cards"]
    entries = load_kanji()
    unlocked = srs.unlocked_levels(entries, cards)
    groups = ("Apprentice", "Guru", "Master", "Enlightened", "Burned")

    print(f"\n{'Kanken':<8}{'New':>5}" + "".join(f"{g:>12}" for g in groups))
    for level in LEVELS:
        if level not in unlocked:
            print(f"{level:<8}(locked)")
            continue
        counts = dict.fromkeys(groups, 0)
        new = 0
        for entry in entries:
            if entry.level != level:
                continue
            if entry.kanji in cards:
                counts[srs.stage_group(cards[entry.kanji]["stage"])] += 1
            else:
                new += 1
        row = "".join(f"{counts[g]:>12}" for g in groups)
        print(f"{level:<8}{new:>5}{row}")

    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    due_now = 0
    due_soon = 0
    for card in cards.values():
        if srs.is_due(card, now):
            due_now += 1
        elif srs.is_due(card, tomorrow):
            due_soon += 1
    lessons = len(srs.available_lessons(entries, cards))
    print(f"\nLessons available: {lessons}")
    print(f"Reviews due now: {due_now}  (and {due_soon} more in 24 hours)")

    current = unlocked[-1]
    needed = srs.guru_needed(entries, cards, current)
    if needed > 0 and current != LEVELS[-1]:
        print(f"Kanken {current}: {needed} more kanji at Guru to unlock the"
              " next level.")
    print()


def bar(percent: float, width: int = 24) -> str:
    filled = round(percent / 100 * width)
    return "█" * filled + "░" * (width - filled)


def cmd_stats_history(args: argparse.Namespace) -> None:
    history = load_progress(Path(args.progress))["history"]
    chosen = LEVELS
    if args.levels:
        chosen = tuple(args.levels.split(","))

    rows = []
    for day in sorted(history)[-args.last:]:
        questions = 0
        correct = 0
        for level, record in history[day].items():
            if level in chosen:
                questions += record["questions"]
                correct += record["correct"]
        if questions:
            rows.append((day, correct, questions, correct / questions * 100))
    if not rows:
        print("No review history yet.")
        return

    print("\nDaily review accuracy (right first time)")
    print("-" * 56)
    for day, correct, questions, percent in rows:
        print(f"{day} | {correct:>3}/{questions:<3} | {percent:5.1f}%"
              f" | {bar(percent)}")
    average = sum(row[3] for row in rows) / len(rows)
    print("-" * 56)
    print(f"Average over {len(rows)} days: {average:.1f}%\n")


def cmd_reset(args: argparse.Namespace) -> None:
    Path(args.progress).unlink(missing_ok=True)
    print(f"Removed {args.progress}")


def cmd_import_kanken(args: argparse.Namespace) -> None:
    total = write_kanken_dataset()
    print(f"Imported {total} kanji into {DATASET}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress", default=PROGRESS,
                        help=f"progress file (default: {PROGRESS})")
    sub = parser.add_subparsers(dest="command", required=True)

    lessons = sub.add_parser("lessons", help="learn new kanji")
    lessons.add_argument("--count", type=int, default=LESSON_BATCH,
                         help=f"kanji per lesson (default: {LESSON_BATCH})")
    lessons.set_defaults(func=cmd_lessons)

    review = sub.add_parser("review", help="review every kanji due now")
    review.set_defaults(func=cmd_review)

    stats = sub.add_parser("stats", help="kanji per SRS stage and level")
    stats.set_defaults(func=cmd_stats)

    history = sub.add_parser("stats-history", help="daily review accuracy")
    history.add_argument("--levels", help="only these levels, e.g. 10,9")
    history.add_argument("--last", type=int, default=30,
                         help="number of recent days (default: 30)")
    history.set_defaults(func=cmd_stats_history)

    reset = sub.add_parser("reset", help="delete all progress")
    reset.set_defaults(func=cmd_reset)

    importer = sub.add_parser("import-kanken",
                              help="rebuild the dataset from KanjiAPI")
    importer.set_defaults(func=cmd_import_kanken)

    args = parser.parse_args()
    try:
        args.func(args)
    except (KeyboardInterrupt, EOFError):
        # Reviews and lessons save as they go, so nothing answered is lost.
        raise SystemExit("\nStopped.")


if __name__ == "__main__":
    main()
