from __future__ import annotations

import argparse
from datetime import datetime
import random
import re
from pathlib import Path

from .data_loader import KanjiEntry, level_sort_value, load_kanji
from .importer import LEVELS as IMPORT_LEVELS
from .importer import write_kanken_dataset
from .storage import DEFAULT_PROGRESS_FILE, card_state, load_progress, save_progress

VALID_LEVELS = ("10", "9", "8", "7", "6", "5", "4", "3")
DEFAULT_QUIZ_COUNT = 20
MISTAKE_WEIGHT = 1
KANJI_STYLE = ""
STYLE_RESET = ""
SYNONYM_CANONICAL = {
    "usage": "use",
    "utilize": "use",
    "utilization": "use",
    "employ": "use",
    "employed": "use",
    "plump": "fat",
    "thick": "fat",
    "chubby": "fat",
}


def normalize_meaning(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", "", text.strip().lower())
    return re.sub(r"\s+", " ", cleaned)


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    if len(left) > len(right):
        left, right = right, left

    previous = list(range(len(left) + 1))
    for index_right, char_right in enumerate(right, start=1):
        current = [index_right]
        for index_left, char_left in enumerate(left, start=1):
            insert_cost = current[index_left - 1] + 1
            delete_cost = previous[index_left] + 1
            replace_cost = previous[index_left - 1] + (char_left != char_right)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current

    return previous[-1]


def max_typo_distance(word: str) -> int:
    compact = word.replace(" ", "")
    length = len(compact)
    if length <= 5:
        return 1
    if length <= 10:
        return 2
    return 3


def is_single_adjacent_transposition(left: str, right: str) -> bool:
    if len(left) != len(right) or left == right:
        return False

    mismatches = [index for index, (a, b) in enumerate(
        zip(left, right)) if a != b]
    if len(mismatches) != 2:
        return False

    first, second = mismatches
    if second != first + 1:
        return False

    return left[first] == right[second] and left[second] == right[first]


def typo_tolerant_match(guess: str, accepted_meaning: str) -> bool:
    if abs(len(guess) - len(accepted_meaning)) > 3:
        return False

    if min(len(guess), len(accepted_meaning)) <= 3:
        return False

    if is_single_adjacent_transposition(guess, accepted_meaning):
        return True

    distance = levenshtein_distance(guess, accepted_meaning)
    return distance <= max_typo_distance(accepted_meaning)


def base_word_form(word: str) -> str:
    value = word.strip().lower()
    if len(value) <= 3:
        return value

    if value.endswith("ies") and len(value) > 4:
        return value[:-3] + "y"

    for suffix in ("ingly", "edly", "ing", "ed", "ers", "er", "es", "s", "ly"):
        if value.endswith(suffix) and len(value) - len(suffix) >= 3:
            root = value[:-len(suffix)]
            if len(root) >= 2 and root[-1] == root[-2]:
                root = root[:-1]
            return root

    return value


def canonical_word(word: str) -> str:
    base = base_word_form(word)
    return SYNONYM_CANONICAL.get(base, base)


def word_form_match(guess: str, accepted_meaning: str) -> bool:
    guess_tokens = [canonical_word(token) for token in guess.split() if token]
    accepted_tokens = [canonical_word(token)
                       for token in accepted_meaning.split() if token]

    if not guess_tokens or not accepted_tokens:
        return False

    if guess_tokens == accepted_tokens:
        return True

    if len(guess_tokens) == 1:
        guess_word = guess_tokens[0]
        if len(guess_word) < 4:
            return False
        return guess_word in accepted_tokens

    if len(guess_tokens) == len(accepted_tokens):
        return all(left == right for left, right in zip(guess_tokens, accepted_tokens))

    return False


def is_correct_answer(answer: str, meanings: tuple[str, ...]) -> bool:
    guess = normalize_meaning(answer)
    accepted = {normalize_meaning(item) for item in meanings}
    if guess in accepted:
        return True

    if not guess:
        return False

    if any(word_form_match(guess, meaning) for meaning in accepted):
        return True

    return any(typo_tolerant_match(guess, meaning) for meaning in accepted)


def summarize_meanings(meanings: tuple[str, ...]) -> str:
    return ", ".join(meanings)


def format_percent(value: float) -> str:
    return f"{value:.1f}%"


def bar_for_percent(value: float, width: int = 20) -> str:
    clamped = max(0.0, min(100.0, value))
    filled = round((clamped / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return int(text)
        except ValueError:
            return default
    return default


def _daily_accuracy(correct: int, questions: int) -> float:
    return (correct / questions) * 100 if questions else 0.0


def _ensure_daily_history(progress: dict) -> dict[str, dict]:
    daily = progress.setdefault("daily_history", {})
    if isinstance(daily, dict):
        return daily

    progress["daily_history"] = {}
    return progress["daily_history"]


def save_daily_result(
    progress: dict,
    *,
    level: str,
    questions: int,
    correct: int,
) -> None:
    incorrect = questions - correct
    day_key = datetime.now().date().isoformat()

    daily_history = _ensure_daily_history(progress)
    day_record = daily_history.setdefault(
        day_key,
        {
            "questions": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
            "levels": {},
        },
    )

    day_record["questions"] = _safe_int(
        day_record.get("questions")) + questions
    day_record["correct"] = _safe_int(day_record.get("correct")) + correct
    day_record["incorrect"] = _safe_int(
        day_record.get("incorrect")) + incorrect
    day_record["accuracy"] = round(
        _daily_accuracy(day_record["correct"], day_record["questions"]),
        2,
    )

    levels = day_record.setdefault("levels", {})
    if not isinstance(levels, dict):
        levels = {}
        day_record["levels"] = levels

    level_record = levels.setdefault(
        level,
        {
            "questions": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
        },
    )
    level_record["questions"] = _safe_int(
        level_record.get("questions")) + questions
    level_record["correct"] = _safe_int(level_record.get("correct")) + correct
    level_record["incorrect"] = _safe_int(
        level_record.get("incorrect")) + incorrect
    level_record["accuracy"] = round(
        _daily_accuracy(level_record["correct"], level_record["questions"]),
        2,
    )


def parse_levels(levels_raw: str | None) -> set[str] | None:
    if not levels_raw:
        return None
    parsed = {item.strip() for item in levels_raw.split(",") if item.strip()}
    return {level for level in parsed if level in VALID_LEVELS}


def choose_level(level_arg: str | None) -> str:
    if level_arg:
        if level_arg not in VALID_LEVELS:
            raise ValueError(
                "Kanken level must be between 10 and 3.")
        return level_arg

    print("Choose a Kanken level for this quiz:")
    print("10 = easiest ... 3 = hardest")

    while True:
        selected = input("Level [10-3]: ").strip()
        if selected in VALID_LEVELS:
            return selected
        print("Invalid level. Please enter one of: 10, 9, 8, 7, 6, 5, 4, 3")


def choose_count(count_arg: int | None, max_available: int) -> int:
    if max_available <= 0:
        raise ValueError("No kanji are available for the selected level.")

    if count_arg is not None:
        if count_arg < 1:
            raise ValueError("Question count must be at least 1.")
        if count_arg > max_available:
            raise ValueError(
                f"Question count must be <= {max_available} for this level.")
        return count_arg

    default_count = min(DEFAULT_QUIZ_COUNT, max_available)
    print(f"How many kanji do you want to be tested on? (1-{max_available})")

    while True:
        raw = input(f"Count [{default_count}]: ").strip()
        if not raw:
            return default_count
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= max_available:
                return selected
        print(f"Invalid count. Enter a number from 1 to {max_available}.")


def mistake_count(state: dict) -> int:
    stored = _safe_int(state.get("mistakes"))
    if stored > 0:
        return stored

    attempts = _safe_int(state.get("attempts"))
    correct = _safe_int(state.get("correct"))
    return max(0, attempts - correct)


def weighted_sample_without_replacement(
    entries: list[KanjiEntry],
    weights: list[int],
    count: int,
) -> list[KanjiEntry]:
    if count <= 0:
        return []

    pool = list(entries)
    pool_weights = list(weights)
    selected: list[KanjiEntry] = []

    for _ in range(min(count, len(pool))):
        index = random.choices(range(len(pool)), weights=pool_weights, k=1)[0]
        selected.append(pool.pop(index))
        pool_weights.pop(index)

    return selected


def pick_quiz_cards_weighted(
    entries: list[KanjiEntry],
    progress: dict,
    level: str,
    count: int,
) -> list[KanjiEntry]:
    level_entries = [entry for entry in entries if entry.level == level]
    if not level_entries:
        return []

    if len(level_entries) < count:
        return []

    cards = progress.get("cards", {})
    weights: list[int] = []
    for entry in level_entries:
        state = cards.get(entry.kanji, {})
        misses = mistake_count(state)
        weights.append(1 + (MISTAKE_WEIGHT * misses))

    return weighted_sample_without_replacement(level_entries, weights, count)


def print_stats(entries: list[KanjiEntry], progress: dict, allowed_levels: set[str] | None = None) -> None:
    cards = progress.get("cards", {})
    levels = sorted(
        {entry.level for entry in entries if entry.level in VALID_LEVELS},
        key=level_sort_value,
    )

    print("\nProgress by Kanken level")
    print("-" * 34)
    total_seen = 0
    total_misses = 0
    total_all = 0

    for level in levels:
        if allowed_levels is not None and level not in allowed_levels:
            continue

        level_entries = [entry for entry in entries if entry.level == level]
        total = len(level_entries)
        seen = sum(1 for entry in level_entries if entry.kanji in cards)
        miss_count = sum(
            mistake_count(cards.get(entry.kanji, {}))
            for entry in level_entries
            if entry.kanji in cards
        )

        total_all += total
        total_seen += seen
        total_misses += miss_count

        print(
            f"Level {level:>2}: seen {seen:>3}/{total:<3} | misses {miss_count:>3}")

    print("-" * 34)
    print(
        f"Total     : seen {total_seen}/{total_all} | misses {total_misses}\n")


def cmd_init(progress_path: Path) -> None:
    save_progress(progress_path, {"cards": {}})
    print(f"Initialized progress file at: {progress_path}")


def cmd_reset(progress_path: Path) -> None:
    if progress_path.exists():
        progress_path.unlink()
    print(f"Reset complete. Removed: {progress_path}")


def cmd_import_kanken(_: argparse.Namespace) -> None:
    dataset_path = Path(__file__).with_name(
        "data").joinpath("kanji_kanken.json")
    total = write_kanken_dataset(dataset_path, levels=IMPORT_LEVELS)
    print(f"Imported {total} kanji records into: {dataset_path}")


def cmd_stats_history(args: argparse.Namespace) -> None:
    progress_path = Path(args.progress).resolve()
    levels = parse_levels(args.levels)
    progress = load_progress(progress_path)

    daily_history = progress.get("daily_history", {})
    if not isinstance(daily_history, dict) or not daily_history:
        print("No daily history found. Run some review sessions first.")
        return

    last = max(1, args.last)

    day_keys = sorted(daily_history.keys())
    recent_day_keys = day_keys[-last:]

    rows: list[tuple[str, int, int, float]] = []
    for day_key in recent_day_keys:
        day_record = daily_history.get(day_key, {})
        if not isinstance(day_record, dict):
            continue

        if levels is None:
            questions = _safe_int(day_record.get("questions"))
            correct = _safe_int(day_record.get("correct"))
        else:
            level_map = day_record.get("levels", {})
            if not isinstance(level_map, dict):
                continue

            questions = 0
            correct = 0
            for level in levels:
                level_record = level_map.get(level, {})
                if not isinstance(level_record, dict):
                    continue
                questions += _safe_int(level_record.get("questions"))
                correct += _safe_int(level_record.get("correct"))

        if questions == 0:
            continue

        rows.append((day_key, correct, questions,
                    _daily_accuracy(correct, questions)))

    if not rows:
        print("No daily history for the selected levels.")
        return

    print("\nDaily Accuracy History")
    print("-" * 72)
    for day_key, correct, questions, accuracy in rows:
        bar = bar_for_percent(accuracy, width=24)
        print(
            f"{day_key} | {correct:>3}/{questions:<3} | {format_percent(accuracy):>6} | {bar}")

    avg = sum(item[3] for item in rows) / len(rows)
    latest = rows[-1][3]
    print("-" * 72)
    print(
        f"Latest: {format_percent(latest)} | Average ({len(rows)} days): {format_percent(avg)}")

    print("")


def run_review(
    entries: list[KanjiEntry],
    progress: dict,
    progress_path: Path,
    level: str,
    count: int,
) -> None:
    queue = pick_quiz_cards_weighted(
        entries,
        progress,
        level=level,
        count=count,
    )

    if not queue:
        level_size = sum(1 for entry in entries if entry.level == level)
        if level_size == 0:
            print("No kanji found for the selected level.")
            return

        print(
            f"Level {level} has only {level_size} unique kanji, but the quiz requires {count} unique kanji.")
        print(
            "Please add more kanji to that level in the dataset before running this quiz.")
        return

    correct_total = 0
    results: list[tuple[KanjiEntry, str, bool]] = []

    for index, entry in enumerate(queue, start=1):
        print(f"\n[{index}/{len(queue)}] Level {entry.level}")
        print(f"Kanji: {KANJI_STYLE}{entry.kanji}{STYLE_RESET}")
        answer = input("Meaning: ").strip()

        state_dict = card_state(progress, entry.kanji)

        state_dict["attempts"] += 1

        correct = is_correct_answer(answer, entry.meanings)
        if correct:
            correct_total += 1
            state_dict["correct"] += 1
        else:
            state_dict["mistakes"] = _safe_int(state_dict.get("mistakes")) + 1

        results.append((entry, answer, correct))

    save_daily_result(
        progress,
        level=level,
        questions=len(queue),
        correct=correct_total,
    )
    save_progress(progress_path, progress)

    print("\nQuiz Results")
    print("-" * 34)
    print(f"Level: {level}")
    print(f"Questions: {len(queue)}")
    print(f"Correct: {correct_total}")
    print(f"Incorrect: {len(queue) - correct_total}")
    print(f"Score: {(correct_total / len(queue)) * 100:.1f}%")

    incorrect = [item for item in results if not item[2]]
    if incorrect:
        print("\nReview incorrect answers:")
        for entry, answer, _ in incorrect:
            accepted = summarize_meanings(entry.meanings)
            print(
                f"- {entry.kanji}: your answer='{answer}' | accepted='{accepted}'")


def cmd_review(args: argparse.Namespace) -> None:
    progress_path = Path(args.progress).resolve()
    entries = load_kanji()
    progress = load_progress(progress_path)
    level = choose_level(args.level)
    level_size = sum(1 for entry in entries if entry.level == level)
    count = choose_count(args.count, level_size)

    run_review(
        entries=entries,
        progress=progress,
        progress_path=progress_path,
        level=level,
        count=count,
    )


def cmd_stats(args: argparse.Namespace) -> None:
    progress_path = Path(args.progress).resolve()
    entries = load_kanji()
    levels = parse_levels(args.levels)
    progress = load_progress(progress_path)
    print_stats(entries, progress, allowed_levels=levels)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kanji quiz with mistake tracking (meaning-only)")
    parser.add_argument(
        "--progress",
        default=DEFAULT_PROGRESS_FILE,
        help=f"Progress JSON file path (default: {DEFAULT_PROGRESS_FILE})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Initialize progress file")
    init_cmd.set_defaults(func=lambda args: cmd_init(
        Path(args.progress).resolve()))

    reset_cmd = sub.add_parser("reset", help="Reset progress file")
    reset_cmd.set_defaults(func=lambda args: cmd_reset(
        Path(args.progress).resolve()))

    review_cmd = sub.add_parser("review", help="Run review session")
    review_cmd.add_argument(
        "--level",
        default=None,
        help="Kanken level for this quiz (10-3). If omitted, you will be prompted.",
    )
    review_cmd.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of kanji questions for this run. If omitted, you will be prompted after level selection.",
    )
    review_cmd.set_defaults(func=cmd_review)

    stats_cmd = sub.add_parser("stats", help="Show progress stats")
    stats_cmd.add_argument(
        "--levels",
        default=None,
        help="Comma-separated Kanken levels to include, e.g. 10,9,8",
    )
    stats_cmd.set_defaults(func=cmd_stats)

    stats_history_cmd = sub.add_parser(
        "stats-history",
        help="Show session history with per-level terminal chart",
    )
    stats_history_cmd.add_argument(
        "--levels",
        default=None,
        help="Comma-separated Kanken levels to include, e.g. 10,9,8",
    )
    stats_history_cmd.add_argument(
        "--last",
        type=int,
        default=20,
        help="Number of recent sessions to include (default: 20)",
    )
    stats_history_cmd.set_defaults(func=cmd_stats_history)

    import_cmd = sub.add_parser(
        "import-kanken",
        help="Import kanji+English meanings from KanjiAPI bulk data into levels 10 to 3",
    )
    import_cmd.set_defaults(func=cmd_import_kanken)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
