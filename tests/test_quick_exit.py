import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import cv2
import numpy as np
import time

from test_queue_selection import extract
from trophy_observer import MatchResult


class QuickExitTests(unittest.TestCase):
    def test_solo_ranks_and_live_counter(self):
        ns = extract('state_finder.py', {'read_solo_result'},
                     {'cv2': cv2, 'time': time, '_rank_read_times': {}})
        frame = np.zeros((1080,1920,3), dtype=np.uint8)
        with patch.dict('sys.modules', {'trophy_reader': SimpleNamespace(available=lambda: True)}):
            for text, expected in [('Rank: 8', 'defeat'), ('Rank: 10','defeat'), ('Rank: 4','victory'), ('Brawlers left: 7',False)]:
                ns['_rank_read_times'].clear()
                with patch('pytesseract.image_to_string', return_value=text):
                    self.assertEqual(ns['read_solo_result'](frame), expected)

    def test_short_match_exits_without_waiting_25_seconds(self):
        ns = extract('stage_manager.py', {'end_game'}, {
            'get_state': lambda frame: frame, 'time': SimpleNamespace(time=lambda:100),
            'is_underdog': lambda _:False, 'save_brawler_data':Mock(), 'MatchResult':MatchResult,
        }, 'StageManager')
        observer = Mock(current_trophies=39, current_wins=0, win_streak=0)
        observer.parse_game_result.return_value = SimpleNamespace(result=MatchResult.DEFEAT)
        wc = Mock()
        obj = SimpleNamespace(window_controller=wc, Trophy_observer=observer,
            _end_result_recorded=False, time_since_last_stat_change=99,
            brawlers_pick_data=[{'brawler':'shelly','type':'trophies'}],
            playstyle_info={}, play_again_on_win=False,
            _should_stop=lambda:False, _should_pause=lambda:False,
            _sleep_interruptible=Mock(return_value=False))
        with patch('lobby_automation.selection_snapshot', side_effect=['end_defeat','lobby']):
            ns['end_game'](obj)
        wc.press.assert_called_once_with('proceed')
        observer.add_trophies.assert_called_once()
        obj._sleep_interruptible.assert_called_once_with(.4)


if __name__ == '__main__':
    unittest.main()
