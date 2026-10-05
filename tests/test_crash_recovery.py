"""Crash recovery must work even when the launcher is classified as a match."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from test_queue_selection import extract


class CrashRecoveryTests(unittest.TestCase):
    def test_direct_activity_launch_retries_until_foreground_confirmed(self):
        ns = extract("window_controller.py", {"start_brawl_stars_activity"},
                     {"time": SimpleNamespace(sleep=Mock())}, "WindowController")
        device = Mock()
        device.shell.side_effect = ["priority=0\ncom.supercell.brawlstars/.GameApp\n", "Status: ok", "Status: ok"]
        controller = SimpleNamespace(BRAWL_STARS_PACKAGE="com.supercell.brawlstars",
                                     serial="emulator-5554", device=device,
                                     is_brawl_stars_running=Mock(side_effect=[False, True]))
        ns["start_brawl_stars_activity"](controller)
        self.assertEqual(device.shell.call_count, 3)
        device.shell.assert_called_with(
            ["am", "start", "-W", "-n", "com.supercell.brawlstars/.GameApp"], timeout=20)
        device.app_start.assert_not_called()

    def test_failed_launch_is_reported(self):
        ns = extract("window_controller.py", {"start_brawl_stars_activity"},
                     {"time": SimpleNamespace(sleep=Mock())}, "WindowController")
        device = Mock()
        device.shell.return_value = "No activity found"
        controller = SimpleNamespace(BRAWL_STARS_PACKAGE="com.supercell.brawlstars",
                                     serial="emulator-5554", device=device,
                                     is_brawl_stars_running=lambda: False)
        with self.assertRaises(ConnectionError):
            ns["start_brawl_stars_activity"](controller)
        self.assertEqual(device.app_start.call_count, 3)

    def run_check(self, alive, foreground, state="match", last_check=0):
        ns = extract("bot_instance.py", {"check_and_handle_brawl_stars_crash"},
                     {"time": SimpleNamespace(time=lambda: 100), "AdbError": RuntimeError},
                     "BotInstance")
        controller = Mock()
        controller.brawl_stars_process_alive.return_value = alive
        controller.is_brawl_stars_running.return_value = foreground
        bot = SimpleNamespace(window_controller=controller, device_label="test",
                              time_since_checked_if_brawl_stars_crashed=last_check,
                              check_if_brawl_stars_crashed_timer=5,
                              get_latest_state=lambda: state,
                              restart_brawl_stars=Mock())
        ns["check_and_handle_brawl_stars_crash"](bot)
        return bot, controller

    def test_launcher_with_live_background_process_reopens_game(self):
        for state in ("match", "match_making", "lobby"):
            with self.subTest(state=state):
                bot, controller = self.run_check(True, False, state)
                controller.launch_brawl_stars.assert_called_once_with()
                self.assertEqual(bot.time_since_checked_if_brawl_stars_crashed, 100)

    def test_dead_process_reopens_game(self):
        _, controller = self.run_check(False, False)
        controller.launch_brawl_stars.assert_called_once_with()

    def test_running_foreground_game_is_left_alone(self):
        _, controller = self.run_check(True, True)
        controller.launch_brawl_stars.assert_not_called()

    def test_checks_are_throttled(self):
        _, controller = self.run_check(False, False, last_check=98)
        controller.brawl_stars_process_alive.assert_not_called()
        controller.launch_brawl_stars.assert_not_called()


if __name__ == "__main__":
    unittest.main()
