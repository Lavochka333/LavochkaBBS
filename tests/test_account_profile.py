import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import numpy as np
from test_queue_selection import extract


class AccountProfileTests(unittest.TestCase):
    def test_open_profile_is_not_clicked_back_before_reading(self):
        frame = np.zeros((900,1600,3), dtype=np.uint8)
        details = Mock(return_value=('80929RRQL0',1))
        ns = extract('account_roster.py', {'identify'}, {'np':np,
            'profile_details':details, 'time':SimpleNamespace(sleep=lambda _:None)})
        wc = Mock()
        wc.device.screenshot.return_value = frame
        with patch.dict('sys.modules', {'state_finder':SimpleNamespace(is_in_lobby=lambda _:False)}):
            self.assertEqual(ns['identify'](wc), ('80929RRQL0',1))
        wc.click.assert_called_once_with(84,45,already_include_ratio=False)

    def test_profile_requires_both_tag_and_collected_count(self):
        import re
        ocr = Mock(side_effect=['1 / 107 Collected','#80929RRQL0'])
        ns = extract('account_roster.py', {'profile_details'}, {'re':re,'_ocr':ocr})
        self.assertEqual(ns['profile_details'](None), ('80929RRQL0',1))
        ocr.side_effect = ['Brawlers']
        self.assertIsNone(ns['profile_details'](None))
