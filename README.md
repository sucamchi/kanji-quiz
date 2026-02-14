# Kanji Test (Python 3)

[![Python >=3.10](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/downloads/)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-brightgreen)](pyproject.toml)
[![Type CLI](https://img.shields.io/badge/type-CLI-informational)](kanji_test/cli.py)

A command-line quiz for Japanese kanji with mistake-weighted review.

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
  - `misses`: how many incorrect answers you've logged for that level
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

## Mistake weighting

The quiz stores mistake counts per kanji in `progress.json` and biases selection
toward items you miss more often. A single quiz still contains unique kanji; the
weighting only affects which cards are more likely to appear between sessions.
