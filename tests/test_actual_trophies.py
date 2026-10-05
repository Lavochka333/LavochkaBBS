"""Match rewards must come from consecutive confirmed game counters."""
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from test_queue_selection import extract
from trophy_observer import MatchResult, ParsedGameResult, GameMode
from datetime import datetime


class ActualTrophiesTests(unittest.TestCase):
    def setUp(self):
        methods = extract('trophy_observer.py', {'add_trophies', 'confirm_trophies'}, {
            'MatchResult': MatchResult, 'ParsedGameResult': ParsedGameResult,
            'datetime': datetime, 'hash_playstyle': lambda _: '', 'XLAMBOT_VERSION': 'test',
        }, class_name='TrophyObserver')
        self.add = methods['add_trophies']
        self.confirm = methods['confirm_trophies']
        self.observer = SimpleNamespace(current_trophies=39, trophies_confirmed=True,
            win_streak=0, current_wins=0, match_history=[], match_counter=0,
            save_history=Mock(), send_results_to_api=Mock(), record_trophy_sample=Mock(),
            pending_trophy_match=None)

    def test_reward_waits_for_actual_counter_and_allows_private_server_rewards(self):
        result = ParsedGameResult(GameMode.CLASSIC, MatchResult.VICTORY, None, 'victory')
        self.add(self.observer, result, 'shelly', {}, False)
        self.assertEqual(self.observer.current_trophies, 39)
        self.assertIsNone(self.observer.match_history[-1]['trophy_delta'])
        self.assertFalse(self.observer.trophies_confirmed)
        self.confirm(self.observer, 64, 'shelly')
        self.assertEqual(self.observer.match_history[-1]['trophy_delta'], 25)
        self.assertEqual(self.observer.current_trophies, 64)

    def test_unknown_baseline_does_not_invent_reward(self):
        self.observer.trophies_confirmed = False
        result = ParsedGameResult(GameMode.CLASSIC, MatchResult.DEFEAT, None, 'defeat')
        self.add(self.observer, result, 'shelly', {}, False)
        self.confirm(self.observer, 10, 'shelly')
        self.assertIsNone(self.observer.match_history[-1]['trophy_delta'])

    def test_different_fighter_cannot_resolve_previous_reward(self):
        self.observer.pending_trophy_match = {'brawler_name':'shelly', 'current_trophies':39}
        self.confirm(self.observer, 521, 'barley')
        self.assertNotIn('trophy_delta', self.observer.pending_trophy_match)


if __name__ == '__main__':
    unittest.main()
