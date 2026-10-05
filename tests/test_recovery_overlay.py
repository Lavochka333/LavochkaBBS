"""Overlay recognition and recovery without a running emulator."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
from test_queue_selection import extract, ROOT


class RecoveryOverlayTests(unittest.TestCase):
    def setUp(self):
        self.find = extract("state_finder.py", {"find_recovery_overlay"}, {
            "cv2": cv2, "cached_templates": {},
            "states_path": str(ROOT / "images" / "states") + "/",
        })["find_recovery_overlay"]

    def test_reload_position_at_multiple_resolutions(self):
        source = cv2.imread(str(ROOT / "images/states/reload_button.png"))
        for scale in (1, 2):
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            frame[300:308, 400:426] = source
            frame = cv2.resize(frame, None, fx=scale, fy=scale)
            state = self.find(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            _, x, y = state.split(":")
            self.assertAlmostEqual(int(x), 413 * scale, delta=2)
            self.assertAlmostEqual(int(y), 304 * scale, delta=2)

    def test_idle_warning_and_empty_screen(self):
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        self.assertIsNone(self.find(frame))
        source = cv2.imread(str(ROOT / "images/states/idle_warning.png"))
        frame[100:113, 300:455] = source
        self.assertEqual(self.find(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), "idle_warning")

    def test_ordinary_saved_frames_are_not_overlays(self):
        for path in (ROOT / "debug_shots").glob("*.png"):
            frame = cv2.imread(str(path))
            if frame is not None:
                self.assertIsNone(self.find(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), path.name)

    def test_promotion_and_close_button(self):
        frame = np.zeros((243, 371, 3), dtype=np.uint8)
        source = cv2.imread(str(ROOT / "images/states/promo_watch.png"))
        frame[205:236, 138:232] = source
        self.assertEqual(self.find(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), "promo_popup")
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        source = cv2.imread(str(ROOT / "images/states/close_popup.png"))
        frame[140:198, 1740:1826] = source
        state = self.find(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.assertTrue(state.startswith("popup_close:"), state)

    def test_promotion_goes_back_without_opening_video(self):
        action = extract("stage_manager.py", {"handle_recovery_overlay"}, {
            "time": SimpleNamespace(monotonic=lambda: 100),
        }, "StageManager")["handle_recovery_overlay"]
        controller = Mock()
        manager = SimpleNamespace(window_controller=controller, _should_stop=lambda: False)
        action(manager, "promo_popup")
        controller.dismiss_popup.assert_called_once_with()
        controller.click.assert_not_called()
        action(manager, "popup_close:1783:169")
        controller.click.assert_called_once_with(1783, 169)

    def test_actions_are_throttled_and_movement_is_released(self):
        action = extract("stage_manager.py", {"handle_recovery_overlay"}, {
            "time": SimpleNamespace(monotonic=lambda: 100),
        }, "StageManager")["handle_recovery_overlay"]
        controller = Mock(width_ratio=1)
        manager = SimpleNamespace(window_controller=controller,
                                  _should_stop=lambda: False, _sleep_interruptible=Mock())
        action(manager, "idle_warning")
        action(manager, "idle_warning")
        controller.move.assert_called_once_with(55, 0)
        self.assertEqual(controller.release_movement.call_count, 2)
        action(manager, "reload:420:300")
        controller.click.assert_called_once_with(420, 300)

    def test_movement_released_if_wait_fails(self):
        action = extract("stage_manager.py", {"handle_recovery_overlay"}, {
            "time": SimpleNamespace(monotonic=lambda: 100),
        }, "StageManager")["handle_recovery_overlay"]
        controller = Mock(width_ratio=1)
        manager = SimpleNamespace(window_controller=controller,
                                  _should_stop=lambda: False,
                                  _sleep_interruptible=Mock(side_effect=RuntimeError))
        with self.assertRaises(RuntimeError):
            action(manager, "idle_warning")
        self.assertEqual(controller.release_movement.call_count, 2)
