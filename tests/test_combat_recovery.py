import unittest
from unittest.mock import Mock, patch

import numpy as np

from play import Play
from utils import load_playstyle_script


class CombatRecoveryTests(unittest.TestCase):
    def make_play(self, style="team_showdown.xlambot"):
        controller = Mock()
        controller.scale_factor = 1
        controller.width_ratio = 1
        controller.height_ratio = 1
        _, source = load_playstyle_script(style)
        with patch("play.Detect"):
            bot = Play("main", "tile", "close", controller, source)
        bot.current_brawler = "shelly"
        bot.frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        bot.unstuck_movement_if_needed = lambda movement, now: movement
        bot.is_there_poison_gas = Mock(return_value=dict(up=0, down=0, left=0, right=0))
        return bot

    def data(self):
        return dict(player=[[900, 450, 960, 550]], enemy=[], teammate=[], wall=[], bush=[])

    def test_unchanged_frames_do_not_starve_direction_change(self):
        bot = self.make_play()
        bot.get_movement = Mock(return_value=(0, -75))
        bot.last_movement = bot.clamp_movement((0, -75))
        bot.last_movement_change_time = 10
        with patch("play.time.time", return_value=10.09):
            bot.loop("shelly", self.data(), 10.09)
        bot.get_movement.return_value = (75, 0)
        with patch("play.time.time", return_value=10.11):
            movement = bot.loop("shelly", self.data(), 10.11)
        self.assertEqual(movement, bot.clamp_movement((75, 0)))

    def test_lost_target_releases_held_attack(self):
        bot = self.make_play()
        bot.get_movement = Mock(return_value=(0, -75))
        bot.persistent_data["time_since_holding_attack"] = 1
        bot.loop("shelly", self.data(), 10)
        bot.window_controller.press.assert_called_once_with("attack", touch_up=True, touch_down=False)
        self.assertIsNone(bot.persistent_data["time_since_holding_attack"])

    def test_nearby_teammate_does_not_stop_movement(self):
        bot = self.make_play()
        data = self.data()
        data['teammate'] = [[920, 450, 980, 550]]
        movement = bot.loop("shelly", data, 10)
        self.assertIsNotNone(movement)
        self.assertGreater(np.hypot(*movement), 0)

    def test_missing_player_in_match_does_not_tap_lobby_button(self):
        bot = self.make_play()
        bot.get_main_data = Mock(return_value={})
        bot.get_tile_data = Mock(return_value={})
        bot.publish_debug_view = Mock()
        bot.time_since_last_proceeding = 0
        main = Mock()
        main.get_latest_state.return_value = "match"
        with patch("play.get_state", return_value="match"):
            bot.main(bot.frame, "shelly", main)
        bot.window_controller.press.assert_not_called()

    def test_gas_escape_overrides_idle_style(self):
        bot = self.make_play()
        bot.get_movement = Mock(return_value=(0, 0))
        movement = bot.loop("shelly", self.data(), 10, gas_movement=(75, 0))
        self.assertEqual(movement, bot.clamp_movement((75, 0)))


if __name__ == "__main__":
    unittest.main()
