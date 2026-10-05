import unittest
from pathlib import Path
from unittest.mock import Mock

import cv2
import numpy as np

from test_queue_selection import extract, ROOT


class CoinRewardTests(unittest.TestCase):
    def setUp(self):
        self.ns = extract('state_finder.py', {'is_in_coins_reward'}, {
            'cv2': cv2, 'cached_templates': {},
            'states_path': str(ROOT / 'images' / 'states') + '/',
        })

    def test_reward_at_emulator_resolutions_and_changed_amount(self):
        frame = np.full((264, 456, 3), (0, 65, 180), np.uint8)
        frame[65:163, 100:374] = cv2.cvtColor(
            cv2.imread(str(ROOT / 'images/states/coins_reward.png')), cv2.COLOR_BGR2RGB)
        for width, height in [(456, 264), (960, 540), (1920, 1080)]:
            resized = cv2.resize(frame, (width, height))
            self.assertTrue(self.ns['is_in_coins_reward'](resized))

    def test_ordinary_frames_are_not_rewards(self):
        self.assertFalse(self.ns['is_in_coins_reward'](np.zeros((264, 456, 3), np.uint8)))
        for path in (ROOT / 'debug_shots').glob('*.png'):
            frame = cv2.imread(str(path))
            if frame is not None:
                self.assertFalse(self.ns['is_in_coins_reward'](cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), path.name)

    def test_reward_takes_priority_over_match_checks(self):
        ns = extract('state_finder.py', {'get_in_game_state'}, {
            'last_debug_print_time': 0, 'should_print_debug_info': False,
            'config_bool': lambda value, default: False,
            'load_toml_as_dict': lambda _: {},
            'time': Mock(time=lambda: 1),
            'is_in_connection_lost': lambda _: False,
            'find_recovery_overlay': lambda _: None,
            'is_in_coins_reward': lambda _: True,
        })
        self.assertEqual(ns['get_in_game_state'](None), 'coins_reward')


if __name__ == '__main__':
    unittest.main()
