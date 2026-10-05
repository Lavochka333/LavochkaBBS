import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import numpy as np
from test_queue_selection import extract


class AccountProfileTests(unittest.TestCase):
    def identify_sequence(self, readings):
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        details = Mock(side_effect=[('2PPYQLGR', 3)] + readings)
        ns = extract('account_roster.py', {'identify'}, {'np': np,
            'profile_details': details, 'time': SimpleNamespace(sleep=lambda _: None)})
        wc = Mock(serial='emulator-5558')
        wc.device.screenshot.return_value = frame
        return ns['identify'], wc

    def test_transient_mismatch_is_rechecked(self):
        identify, wc = self.identify_sequence([
            ('2PPYQLGR', 8), ('2PPYQLGR', 3), ('2PPYQLGR', 3)])
        self.assertEqual(identify(wc), ('2PPYQLGR', 3))
        wc.click.assert_called_once_with(84, 45, already_include_ratio=False)

    def test_unreadable_frame_does_not_confirm_previous_reading(self):
        identify, wc = self.identify_sequence([
            ('2PPYQLGR', 3), ValueError('unreadable tag'),
            ('2PPYQLGR', 3), ('2PPYQLGR', 3)])
        self.assertEqual(identify(wc), ('2PPYQLGR', 3))
        self.assertEqual(wc.device.screenshot.call_count, 5)

    def test_persistent_mismatch_still_blocks_start(self):
        identify, wc = self.identify_sequence([
            ('2PPYQLGR', 3), ('2PPYQLGR', 8)] * 3)
        with self.assertRaisesRegex(ValueError, 'Не удалось подтвердить'):
            identify(wc)
        wc.click.assert_called_once_with(84, 45, already_include_ratio=False)

    def test_owned_card_without_green_upgrade_strip(self):
        from brawler_cards import is_owned_card
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[20:70, 85:96] = (60, 65, 100)
        frame[40:43, 85:96] = (220, 220, 220)
        self.assertTrue(is_owned_card(frame, (0, 0, 100, 100)))

    def test_locked_portrait_is_not_an_owned_card(self):
        from brawler_cards import is_owned_card
        frame = np.full((100, 100, 3), (30, 65, 15), dtype=np.uint8)
        self.assertFalse(is_owned_card(frame, (0, 0, 100, 100)))

    def validator(self):
        normalise = extract('utils.py', {'normalize_brawler_filename'}, {})['normalize_brawler_filename']
        return extract('account_roster.py', {'validate_queue'},
                       {'normalize_brawler_filename': normalise})['validate_queue']

    def test_owned_alias_is_accepted(self):
        self.validator()({'tag': 'same', 'complete': True, 'brawlers': [{'name': 'Mr. P'}]},
                         'same', [{'brawler': 'mrp'}])

    def test_missing_brawler_error_names_the_brawler(self):
        with self.assertRaisesRegex(ValueError, 'colt'):
            self.validator()({'tag': 'same', 'complete': True, 'brawlers': [{'name': 'shelly'}]},
                             'same', [{'brawler': 'colt'}])

    def test_account_change_still_blocks_start(self):
        with self.assertRaisesRegex(ValueError, 'Аккаунт изменился'):
            self.validator()({'tag': 'old', 'brawlers': [{'name': 'shelly'}]},
                             'new', [{'brawler': 'shelly'}])

    def test_open_profile_is_not_clicked_back_before_reading(self):
        frame = np.zeros((900,1600,3), dtype=np.uint8)
        details = Mock(return_value=('2PPYQLGR',1))
        ns = extract('account_roster.py', {'identify'}, {'np':np,
            'profile_details':details, 'time':SimpleNamespace(sleep=lambda _:None)})
        wc = Mock()
        wc.device.screenshot.return_value = frame
        with patch.dict('sys.modules', {'state_finder':SimpleNamespace(is_in_lobby=lambda _:False)}):
            self.assertEqual(ns['identify'](wc), ('2PPYQLGR',1))
        wc.click.assert_called_once_with(84,45,already_include_ratio=False)

    def test_profile_requires_both_tag_and_collected_count(self):
        import re
        ocr = Mock(side_effect=['1 / 107 Collected','#2PPYQLGR'])
        ns = extract('account_roster.py', {'profile_details'}, {'re':re,'_ocr':ocr})
        self.assertEqual(ns['profile_details'](None), ('2PPYQLGR',1))
        ocr.side_effect = ['Brawlers']
        self.assertIsNone(ns['profile_details'](None))
