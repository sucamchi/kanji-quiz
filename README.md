# Kanji Quiz (Python 3)

[![Python >=3.10](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/downloads/)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-brightgreen)](pyproject.toml)
[![Type CLI](https://img.shields.io/badge/type-CLI-informational)](kanji_quiz/cli.py)

A command-line kanji quiz with spaced repetition modelled on WaniKani.
You learn new kanji in small lessons, then review each one at growing
intervals until it is burned. Answers are English meanings only; readings
are not quizzed.

## Quick start

```bash
cd kanji-quiz
python3 -m kanji_quiz.cli lessons   # learn 5 new kanji
python3 -m kanji_quiz.cli review    # review whatever is due
python3 -m kanji_quiz.cli stats
```

Or install it with `pipx install .` and run `kanji-quiz lessons` from
anywhere. After changing the code, run `pipx install --force .` to update
it.

## Commands

- `lessons`: show a batch of new kanji with their meanings, then quiz you
  on them until each is right. `--count 10` changes the batch size
  (default 5).
- `review`: quiz every kanji whose review time has arrived. A wrong answer
  comes back later in the same session until you get it right.
- `stats`: kanji per SRS stage for each Kanken level, reviews due now and
  in the next 24 hours, and how far you are from unlocking the next level.
- `stats-history`: right-first-time accuracy per day, with a bar chart.
  `--last 30` sets how many days, `--levels 10,9` filters levels.
- `reset`: delete all progress.
- `import-kanken`: rebuild the dataset from KanjiAPI
  (`https://kanjiapi.dev/kanjiapi_full.zip`).

All commands take `--progress FILE` (default `progress.json` in the
current folder).

## How the SRS works

Each kanji moves through nine stages. A right answer moves it up one;
the time until its next review is:

| Stage | Next review |
|-------|-------------|
| Apprentice 1 | 4 hours |
| Apprentice 2 | 8 hours |
| Apprentice 3 | 1 day |
| Apprentice 4 | 2 days |
| Guru 1 | 1 week |
| Guru 2 | 2 weeks |
| Master | 1 month |
| Enlightened | 4 months |
| Burned | never again |

Review times are rounded down to the hour, so reviews arrive in batches.

A wrong answer moves the kanji down instead: one stage for every two
misses in that session (rounded up), doubled if the kanji had reached
Guru. It never drops below Apprentice 1.

Lessons start at Kanken 10. The next Kanken level unlocks once 90% of
the current level's kanji are at Guru or higher, all the way down to
Kanken 3.

## Answer matching

- Case, punctuation and extra spaces are ignored.
- Common word endings are ignored, so "descending" counts for "descend".
- Small typos are forgiven in words of four letters or more.
- A single word that appears in a multi-word meaning counts.
- A few synonyms are accepted (see `SYNONYMS` in `kanji_quiz/answers.py`).

## Notes

- Kanken levels are guessed from KanjiAPI's school-grade data, so they
  are approximate. In particular, Kanken 4 collects every secondary-school
  kanji and is much larger than the others.
- Run the tests with `python3 -m unittest discover -s tests`.
