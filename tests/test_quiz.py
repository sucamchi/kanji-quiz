import unittest
from datetime import datetime

from kanji_quiz import srs
from kanji_quiz.answers import is_correct
from kanji_quiz.data_loader import KanjiEntry

NOW = datetime(2026, 11, 2, 14, 30)


class SrsTest(unittest.TestCase):
    def test_new_card_due_in_four_hours_rounded_down(self):
        self.assertEqual(srs.new_card(NOW),
                         {"stage": 1, "due": "2026-11-02T18:00:00"})

    def test_right_answer_moves_up_one_stage(self):
        card = {"stage": 4}
        srs.apply_review(card, 0, NOW)
        self.assertEqual(card["stage"], 5)

    def test_misses_drop_stages_and_double_past_guru(self):
        card = {"stage": 3}
        srs.apply_review(card, 1, NOW)
        self.assertEqual(card["stage"], 2)
        card = {"stage": 7}
        srs.apply_review(card, 3, NOW)  # ceil(3 / 2) * 2 = 4 stages
        self.assertEqual(card["stage"], 3)
        card = {"stage": 2}
        srs.apply_review(card, 5, NOW)
        self.assertEqual(card["stage"], 1)

    def test_burned_card_is_never_due(self):
        card = {"stage": 8}
        srs.apply_review(card, 0, NOW)
        self.assertEqual(card, {"stage": 9, "due": None})
        self.assertFalse(srs.is_due(card, datetime(2100, 1, 1)))

    def test_next_level_unlocks_at_ninety_percent_guru(self):
        entries = [KanjiEntry(str(n), "10", ("x",)) for n in range(10)]
        entries.append(KanjiEntry("a", "9", ("x",)))
        cards = {str(n): {"stage": 5, "due": None} for n in range(8)}
        self.assertEqual(srs.unlocked_levels(entries, cards), ["10"])
        self.assertEqual(srs.guru_needed(entries, cards, "10"), 1)
        cards["8"] = {"stage": 5, "due": None}
        self.assertEqual(srs.unlocked_levels(entries, cards), ["10", "9"])
        lessons = srs.available_lessons(entries, cards)
        self.assertEqual([entry.kanji for entry in lessons], ["9", "a"])


class AnswerTest(unittest.TestCase):
    def test_accepted(self):
        meanings = ("below", "descend", "down")
        for answer in ("Down", "  descending ", "descend!", "beloww"):
            self.assertTrue(is_correct(answer, meanings), answer)
        self.assertTrue(is_correct("sevne", ("seven",)))
        self.assertTrue(is_correct("radical", ("one radical (no.1)",)))
        self.assertTrue(is_correct("utilize", ("use",)))

    def test_rejected(self):
        self.assertFalse(is_correct("", ("one",)))
        self.assertFalse(is_correct("on", ("one",)))
        self.assertFalse(is_correct("up", ("down",)))
        self.assertFalse(is_correct("four", ("five",)))
        self.assertFalse(is_correct("chicken", ("children",)))


if __name__ == "__main__":
    unittest.main()
