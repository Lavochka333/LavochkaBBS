"""Regression checks without GPU, ADB or an installed game."""
import ast
from pathlib import Path
import sys
import types
import re
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def extract(filename, names, namespace, class_name=None):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    nodes = tree.body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    selected = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=selected, type_ignores=[]), filename, "exec"), namespace)
    return namespace


class QueueSelectionTests(unittest.TestCase):
    def setUp(self):
        self.functions = extract("utils.py", {"clean_queue", "normalize_brawler_filename"}, {})

    def test_alias_duplicates_keep_first_entry_and_order(self):
        cleaned = self.functions["clean_queue"]([
            {"brawler": "Mr. P", "trophies": 42},
            {"brawler": "mrp", "trophies": 3000},
            {"brawler": "8-Bit", "wins": "2"}, None,
        ])
        self.assertEqual([e["brawler"] for e in cleaned], ["mrp", "8bit"])
        self.assertEqual(cleaned[0]["trophies"], 42)
        self.assertEqual(cleaned[1]["wins"], 2)
        self.assertEqual(self.functions["clean_queue"](cleaned), cleaned)

    def test_selected_mode_disables_rotation_and_sort(self):
        ns = extract("stage_manager.py", {"brawler_sort_mode", "_switch_after_games", "_pick_lowest_trophies"},
                     {"load_toml_as_dict": lambda _: {"brawler_pick_mode": "selected", "brawler_switch_after_games": 7}}, "StageManager")
        manager = types.SimpleNamespace(BRAWLER_SORT_MODES={"lowest_trophies": "sort"})
        manager.brawler_sort_mode = lambda: ns["brawler_sort_mode"](manager)
        self.assertEqual(ns["_switch_after_games"](manager), 0)
        self.assertFalse(ns["_pick_lowest_trophies"](manager))

    def test_wrong_search_result_is_not_clicked(self):
        normalise = self.functions["normalize_brawler_filename"]
        ns = extract("lobby_automation.py", {"select_brawler"}, {
            "time": types.SimpleNamespace(sleep=lambda _: None),
            "normalize_brawler_filename": normalise,
            "selection_snapshot": lambda controller: controller.screenshot(), "load_brawlers_info": lambda: {},
            "load_toml_as_dict": lambda _: {"brawlers_menu": [110, 490], "first_brawler_icon": [550, 300], "select_brawler": [150, 950]},
        }, "LobbyAutomation")
        controller = Mock(width_ratio=1, height_ratio=1)
        controller.type_text.return_value = True
        selector = types.SimpleNamespace(window_controller=controller,
            _should_interrupt=lambda *args: False, _sleep_interruptible=lambda *args: False, _open_roster=lambda *args: True)
        reader = types.SimpleNamespace(available=lambda: True, read_card=lambda _: {"brawler": "bull", "trophies": 2000})
        with patch.dict(sys.modules, {"trophy_reader": reader}):
            result = ns["select_brawler"](selector, "shelly", lambda: "brawler_selection")
        self.assertEqual(result, "failed")
        self.assertEqual(controller.click.call_count, 0)  # Search result was never tapped.
        self.assertIsNone(selector._last_picked)

    def test_zero_trophies_are_a_valid_measurement(self):
        ns = extract("trophy_reader.py", {"_digits"}, {"re": re})
        self.assertEqual(ns["_digits"]("0"), 0)
        self.assertIsNone(ns["_digits"]("unreadable"))

    def test_ocr_noise_is_not_a_character_name(self):
        ns = extract("trophy_reader.py", {"_match_brawler_name", "_levenshtein"},
                     {"re": re, "NAME_MAX_DISTANCE": 2})
        for noise in ("AAA", "1", "I"):
            self.assertIsNone(ns["_match_brawler_name"](noise, ["tara", "bo", "kit"]))

    def test_russian_labels_and_short_noise(self):
        ns = extract("brawler_cards.py", {"letters", "match_name"},
                     {"re": re, "RUSSIAN_NAMES": {"эльпримо": "elprimo", "бо": "bo"}})
        known = ["elprimo", "tara", "bo", "kit", "jacky"]
        self.assertEqual(ns["match_name"]("ЭЛЬ ПРИМО", known), "elprimo")
        self.assertEqual(ns["match_name"]("IACKY", known), "jacky")
        for noise in ("AAA", "1", "I", "UNLOCKING BRAWLER"):
            self.assertIsNone(ns["match_name"](noise, known))

    def test_large_unlock_offer_is_not_a_card(self):
        import cv2
        import numpy as np
        from brawler_cards import card_boxes
        frame = np.full((900, 1600, 3), (255, 80, 10), dtype=np.uint8)
        cv2.rectangle(frame, (150, 140), (620, 840), (0, 0, 0), 5)
        cv2.rectangle(frame, (780, 140), (1140, 370), (0, 0, 0), 5)
        boxes = card_boxes(frame)
        self.assertEqual(len(boxes), 1)
        self.assertGreater(boxes[0][0], 700)

    def test_already_open_roster_does_not_tap_the_unlock_offer(self):
        ns = extract("lobby_automation.py", {"_open_roster"}, {}, "LobbyAutomation")
        controller = Mock()
        selector = types.SimpleNamespace(window_controller=controller)
        with patch.dict(sys.modules, {
            "brawler_cards": types.SimpleNamespace(card_boxes=lambda _: [(780, 140, 360, 230)]),
            "state_finder": types.SimpleNamespace(is_in_lobby=lambda _: False, is_in_brawler_selection=lambda _: True),
        }):
            self.assertTrue(ns["_open_roster"](selector))
        controller.click.assert_not_called()

    def test_confirmed_card_can_repair_corrupt_saved_trophies(self):
        ns = extract("stage_manager.py", {"_adopt_picked_brawler"}, {}, "StageManager")
        entry = self.functions["clean_queue"]([{"brawler": "shelly", "trophies": 3000}])[0]
        manager = types.SimpleNamespace(
            Lobby_automation=types.SimpleNamespace(last_picked={"brawler": "shelly", "trophies": 42}),
            brawlers_pick_data=[entry], Trophy_observer=Mock(), brawler_sort_mode=lambda: "selected")
        ns["_adopt_picked_brawler"](manager, None, 0)
        self.assertEqual(entry["trophies"], 42)
        manager.Trophy_observer.change_trophies.assert_called_once_with(42)


if __name__ == "__main__":
    unittest.main()
