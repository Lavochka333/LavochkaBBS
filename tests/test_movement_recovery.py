"""Input recovery checks without an emulator or a scrcpy connection."""
import random
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from test_queue_selection import extract


class MovementRecoveryTests(unittest.TestCase):
    def controller(self, now):
        clock = SimpleNamespace(monotonic=lambda: now, sleep=Mock())
        ns = extract('window_controller.py', {'move', 'release_movement'},
                     {'time': clock, 'random': random}, 'WindowController')
        obj = SimpleNamespace(
            are_we_moving=True, movement_touch_started_at=10.0,
            MOVEMENT_TOUCH_REFRESH_INTERVAL=5.0,
            original_movement_joystick=(180, 900),
            movement_joystick_x=180, movement_joystick_y=900,
            width_ratio=1, height_ratio=1, PID_JOYSTICK=1,
            re_apply_movement=False, last_joystick_pos=(230, 900),
            touch_down=Mock(), touch_up=Mock(), touch_move=Mock())
        obj.release_movement = lambda: ns['release_movement'](obj)
        return obj, lambda x, y: ns['move'](obj, x, y)

    def test_same_direction_renews_cancelled_pointer(self):
        obj, move = self.controller(15.0)
        move(50, 0)
        obj.touch_up.assert_called_once_with(180, 900, pointer_id=1)
        obj.touch_down.assert_called_once()
        obj.touch_move.assert_called_once()
        self.assertTrue(obj.are_we_moving)
        self.assertEqual(obj.movement_touch_started_at, 15.0)

    def test_same_direction_before_refresh_avoids_extra_input(self):
        obj, move = self.controller(14.0)
        move(50, 0)
        obj.touch_down.assert_not_called()
        obj.touch_up.assert_not_called()
        obj.touch_move.assert_not_called()

    def test_released_pointer_starts_immediately(self):
        obj, move = self.controller(11.0)
        obj.release_movement()
        move(50, 0)
        obj.touch_down.assert_called_once()
        obj.touch_move.assert_called_once()
        self.assertEqual(obj.movement_touch_started_at, 11.0)

    def run_stale_frame(self, state):
        ns = extract('bot_instance.py', {'main'}, {
            'time': SimpleNamespace(time=lambda: 100.0),
        }, 'BotInstance')
        bot = Mock(runtime_control=None, picked_first_brawler=True,
                   max_fps=0, run_for_minutes=0, in_cooldown=False)
        bot.should_stop.side_effect = [False, True]
        bot.should_pause.return_value = False
        bot.get_latest_state.return_value = state
        bot.window_controller.get_latest_frame.return_value = (None, 80.0)
        bot.window_controller.FRAME_STALE_TIMEOUT = 15.0
        bot.window_controller.is_stream_alive.return_value = True
        bot.window_controller.reconnect_scrcpy.return_value = True
        bot.sleep_interruptible.return_value = None
        ns['main'](bot)
        return bot

    def test_stale_match_reconnects_even_when_stream_thread_is_alive(self):
        bot = self.run_stale_frame('match')
        bot.window_controller.reconnect_scrcpy.assert_called_once()
        bot.Play.main.assert_not_called()
        bot.stop_gracefully.assert_called_once()

    def test_static_lobby_waits_without_reconnecting(self):
        bot = self.run_stale_frame('lobby')
        bot.window_controller.reconnect_scrcpy.assert_not_called()
        bot.sleep_interruptible.assert_called_once_with(0.25)


if __name__ == '__main__':
    unittest.main()
