"""
test_agent.py  -  automatic self-checks.   Run:  python -m unittest -v
ELI5: little experiments that must always give the same answer.  If we
change the code and an experiment fails, we know we broke something.
"""
import unittest
from datetime import datetime

import config
import matcher
import perception
from agent import ASK, NOTIFY, WAIT, LostFoundAgent, decide

NOW = datetime(2026, 11, 16, 18, 0)


class TestPerception(unittest.TestCase):
    def test_synonyms_become_one_category(self):
        for text in ("earphone box", "airpods case", "bluetooth earbuds"):
            self.assertEqual(perception.parse_report("lost", text).category, "earbuds")

    def test_colour_and_brand(self):
        r = perception.parse_report("lost", "navy BOAT earphones")
        self.assertEqual((r.color, r.brand), ("blue", "boat"))

    def test_longer_phrase_wins(self):
        self.assertEqual(perception.parse_report("lost", "black laptop bag").category, "bag")

    def test_location_aliases(self):
        self.assertEqual(perception.resolve_location("near the reading hall"), "library")
        self.assertIsNone(perception.resolve_location("near the big tree"))

    def test_time_parsing(self):
        self.assertEqual(perception.parse_time("2026-11-16 14:30"), datetime(2026, 11, 16, 14, 30))
        self.assertEqual(perception.parse_time("2pm", NOW).hour, 14)


class TestMatcher(unittest.TestCase):
    def test_same_item_beats_different_item(self):
        L = perception.parse_report("lost", "black Boat earbuds case", "library", "2026-11-16 14:00")
        good = perception.parse_report("found", "black earphone box", "reading hall", "2026-11-16 15:00")
        bad = perception.parse_report("found", "brown leather wallet", "canteen", "2026-11-16 15:00")
        ranked = matcher.rank_candidates(L, [bad, good])
        self.assertIs(ranked[0][0], good)
        self.assertGreater(ranked[0][1], ranked[1][1])

    def test_found_before_lost_is_rejected_by_time_rule(self):
        L = perception.parse_report("lost", "umbrella", "", "2026-11-16 14:00")
        F = perception.parse_report("found", "umbrella", "", "2026-11-10 14:00")
        self.assertEqual(matcher.time_score(L, F), 0.0)

    def test_scores_between_0_and_1(self):
        self.assertAlmostEqual(sum(config.WEIGHTS.values()), 1.0)


class TestPolicy(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(decide(0.9, 0.2), NOTIFY)
        self.assertEqual(decide(0.9, 0.85), ASK)       # too close to call
        self.assertEqual(decide(0.6, 0.1), ASK)
        self.assertEqual(decide(0.2, 0.1), WAIT)
        self.assertEqual(decide(None), WAIT)


class TestAgentFlow(unittest.TestCase):
    def setUp(self):
        self.agent = LostFoundAgent()

    def test_wait_then_notify_then_confirm(self):
        r1 = self.agent.handle_report("found", "black earphone box with a sticker", "reading hall",
                                      "2026-11-16 15:30", "ravi", NOW)
        self.assertEqual(r1.action, WAIT)
        r2 = self.agent.handle_report("lost", "black Boat earbuds case, sticker", "library",
                                      "2026-11-16 14:00", "asha", NOW)
        self.assertEqual(r2.action, NOTIFY)
        self.agent.confirm_match(r2.match_id)
        self.assertEqual(self.agent.open_reports(), [])

    def test_reject_is_remembered(self):
        self.agent.handle_report("found", "black earphone box", "library", "2026-11-16 15:30", "ravi", NOW)
        r = self.agent.handle_report("lost", "black Boat earbuds case", "library", "2026-11-16 14:00", "asha", NOW)
        self.assertEqual(r.action, NOTIFY)
        again = self.agent.reject_match(r.match_id)
        self.assertEqual(again.action, WAIT)            # same pair is never suggested again

    def test_vague_report_gets_a_question_and_answer_helps(self):
        self.agent.handle_report("found", "brown leather wallet", "canteen", "2026-11-16 16:00", "meena", NOW)
        r = self.agent.handle_report("lost", "my wallet", "canteen", "2026-11-16 15:00", "karan", NOW)
        self.assertEqual(r.action, ASK)
        r2 = self.agent.answer_question(r.item_id, "it was brown")
        self.assertEqual(r2.action, NOTIFY)

    def test_unrelated_items_do_not_match(self):
        self.agent.handle_report("found", "brown leather wallet", "canteen", "2026-11-16 16:00", "meena", NOW)
        r = self.agent.handle_report("lost", "blue umbrella", "parking", "2026-11-16 09:00", "dev", NOW)
        self.assertEqual(r.action, WAIT)


if __name__ == "__main__":
    unittest.main()
