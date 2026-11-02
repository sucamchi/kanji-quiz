"""Decide whether a typed English meaning counts as correct."""
from __future__ import annotations

from difflib import SequenceMatcher

# Different words for the same idea, mapped to the root of the word the
# dataset uses (roots come from word_root below).
SYNONYMS = {
    "usage": "use",
    "utilize": "use",
    "utilization": "use",
    "employ": "use",
    "plump": "fat",
    "thick": "fat",
    "chubby": "fat",
}

# Checked longest first, so "ingly" wins over "ly".
SUFFIXES = ("ingly", "edly", "ing", "ed", "ers", "er", "es", "s", "ly")


def normalize(text: str) -> str:
    """Lowercase, drop punctuation and squeeze repeated spaces."""
    kept = ""
    for char in text.lower():
        if char.isalnum() or char == " ":
            kept += char
    return " ".join(kept.split())


def word_root(word: str) -> str:
    """Strip a common English ending so "descending" matches "descend"."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            root = word[:-len(suffix)]
            # "running" -> "runn" -> "run"
            if root[-1] == root[-2]:
                root = root[:-1]
            return root
    return word


def root_words(text: str) -> list[str]:
    words = []
    for word in text.split():
        root = word_root(word)
        words.append(SYNONYMS.get(root, root))
    return words


def close_spelling(guess: str, meaning: str) -> bool:
    """Forgive a small typo, like WaniKani does."""
    # Words under 4 letters are too easy to turn into another real word.
    if min(len(guess), len(meaning)) < 4:
        return False
    # 0.8 allows one wrong letter in a five-letter word ("sevne" for
    # "seven") and roughly one per five letters in longer ones.
    return SequenceMatcher(None, guess, meaning).ratio() >= 0.8


def is_correct(answer: str, meanings: tuple[str, ...]) -> bool:
    guess = normalize(answer)
    if not guess:
        return False
    guess_words = root_words(guess)
    for meaning in meanings:
        accepted = normalize(meaning)
        accepted_words = root_words(accepted)
        if guess == accepted or guess_words == accepted_words:
            return True
        # One longer word may match any word of a multi-word meaning.
        single = len(guess_words) == 1 and len(guess_words[0]) >= 4
        if single and guess_words[0] in accepted_words:
            return True
        if close_spelling(guess, accepted):
            return True
    return False
