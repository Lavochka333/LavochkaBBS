"""Starting from the emulator desktop opens the game before account checks."""
import unittest
import numpy as np
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_queue_selection import extract


class StartupLaunchTests(unittest.TestCase):
    def setUp(self):
        self.clock = SimpleNamespace(monotonic=Mock(return_value=10), sleep=Mock())
        self.ns = extract('bot_instance.py', {'wait_for_startup_lobby'},
                          {'time': self.clock, 'BotHalt': RuntimeError}, 'BotInstance')
        self.wc = Mock()
        self.bot = SimpleNamespace(window_controller=self.wc, device_label='test',
                                   should_stop=Mock(return_value=False), stop_event=None)

    def run_start(self, lobby):
        with patch.dict('sys.modules', {'state_finder': SimpleNamespace(is_in_lobby=lobby)}):
            self.ns['wait_for_startup_lobby'](self.bot)

    def test_desktop_launches_then_waits_for_lobby(self):
        self.wc.is_brawl_stars_running.side_effect = [False, True, True]
        lobby = Mock(side_effect=[False, True])
        self.run_start(lobby)
        self.wc.launch_brawl_stars.assert_called_once_with()
        self.assertEqual(self.wc.device.screenshot.call_count, 2)
        self.clock.sleep.assert_called_once_with(1)

    def test_loaded_lobby_does_not_restart_game(self):
        self.wc.is_brawl_stars_running.return_value = True
        self.run_start(Mock(return_value=True))
        self.wc.launch_brawl_stars.assert_not_called()

    def test_stop_during_loading(self):
        self.bot.should_stop.return_value = True
        with self.assertRaisesRegex(RuntimeError, 'остановлен'):
            self.run_start(Mock())
        self.wc.launch_brawl_stars.assert_not_called()

    def test_timeout_is_reported(self):
        self.clock.monotonic.side_effect = [0, 181]
        with self.assertRaisesRegex(RuntimeError, '3 минуты'):
            self.run_start(Mock())


if __name__ == '__main__':
    unittest.main()
