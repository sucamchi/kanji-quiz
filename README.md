# Kanji Test (Python 3)

A command-line spaced repetition quiz for Japanese kanji.

## Features

- Choose one Kanken level before each quiz (10 easiest -> 3 hardest)
- Choose how many kanji to answer per quiz (default: 20)
- Meaning-only answers (English meanings only; readings are ignored)
- End-of-quiz result summary with score and incorrect answer review
- Local progress tracking in JSON

## Quick start

```bash
cd /home/susana/Documents/projects/kanji-test
python3 -m kanji_test.cli init
python3 -m kanji_test.cli import-kanken
python3 -m kanji_test.cli review
python3 -m kanji_test.cli stats
python3 -m kanji_test.cli stats-history
```

## Commands

- `init`: create an empty progress file
- `review`: run a review session
  - asks for Kanken level (`10` to `3`) unless you pass `--level`
  - asks how many questions to run (or pass `--count`)
  - all questions are unique (no repeats in a single quiz)
  - count must be within the selected level's available kanji
  - `--level 10` optional level argument
  - `--count 15` optional question count argument
- `import-kanken`: rebuild dataset from KanjiAPI bulk data (`https://kanjiapi.dev/kanjiapi_full.zip`)
- `stats`: show current progress by level
  - `seen`: how many kanji in that level have been studied at least once
  - `due`: how many studied kanji are scheduled and due for review now
- `stats-history`: show session-by-session accuracy over time
  - shows one aggregated line per day (not per session)
  - prints date, correct/total, accuracy %, and a simple terminal bar chart
  - `--last 30` controls how many recent days to include
  - `--levels 10,9` filters to specific levels
- `reset`: delete progress and start over

## Notes

- Answers are matched against accepted English meanings per kanji.
- Matching is case-insensitive and punctuation-insensitive.
- Small spelling mistakes are tolerated for close matches.
- A small set of common English synonym variants are also accepted.
- Level mapping is heuristic from KanjiAPI metadata to your `10 -> 3` flow.

## SRS behavior

The quiz stores SRS data per kanji in `progress.json` and updates it after every answer.

- Correct answers increase repetition count and usually increase interval.
- Incorrect answers reset repetition and schedule a short interval.
- The SRS scheduler updates:
  - `repetitions`
  - `interval` (days until next review)
  - `ease_factor` (how aggressively interval grows)
  - `due` date

`stats` uses the `due` date to report how many cards are currently due.
