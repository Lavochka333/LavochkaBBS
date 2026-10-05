import ast
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
import math
import random

import numpy as np

from health_reader import estimate_player_health


class CautiousAmbushTests(unittest.TestCase):
    def run_style(self, hp, enemies=(), memory=None, bushes=None, gas=()):
        source = (Path(__file__).resolve().parents[1] / 'playstyles/cautious_ambush.xlambot').read_text(encoding='utf-8')
        json.loads(source.splitlines()[0])
        ast.parse(source)
        attack = Mock()
        context = dict(math=math, random=random, time=Mock(time=Mock(return_value=10.)),
                       player_data=[90, 90, 110, 110], enemy_data=list(enemies),
                       bushes=bushes if bushes is not None else [[70, 70, 130, 130]],
                       gas_boxes=list(gas), walls=[], player_health_ratio=hp, brawler='shelly',
                       TILE_SIZE=50, JOYSTICK_RADIUS=75, persistent_data=memory if memory is not None else {},
                       get_entity_pos=lambda b: ((b[0]+b[2])/2, (b[1]+b[3])/2),
                       get_distance=lambda a, b: math.hypot(a[0]-b[0], a[1]-b[1]),
                       get_brawler_range=lambda b: (80, 200, 200), brawlers_info={'shelly': {}},
                       is_path_blocked=lambda *args: False, is_enemy_hittable=lambda *args: True,
                       must_brawler_hold_attack=lambda *args: False, attack=attack,
                       is_super_ready=False, is_hypercharge_ready=False,
                       seconds_to_hold_attack_after_reaching_max=1.5)
        # Match the real interpreter's available builtins.
        context.update(min=min, max=max, __builtins__={})
        exec(compile(source, '<style>', 'exec'), context)
        return context, attack

    def test_low_and_unknown_hp_stay_hidden_without_attacking(self):
        for hp in (.2, None):
            context, attack = self.run_style(hp, [[190, 90, 210, 110]])
            self.assertEqual(context['movement'], (0, 0))
            attack.assert_not_called()

    def test_healthy_hidden_bot_ambushes_single_nearby_enemy(self):
        context, attack = self.run_style(.9, [[190, 90, 210, 110]])
        self.assertTrue(context['ambushing'])
        self.assertGreater(context['movement'][0], 0)
        attack.assert_called_once_with()

    def test_two_enemies_cancel_ambush(self):
        context, attack = self.run_style(.9, [[190, 90, 210, 110], [190, 130, 210, 150]])
        self.assertFalse(context['ambushing'])
        attack.assert_not_called()

    def test_recovery_does_not_end_at_half_health(self):
        memory = {'cautious_ambush': {'recovering': True}}
        context, attack = self.run_style(.5, [[190, 90, 210, 110]], memory)
        self.assertTrue(context['cautious'])
        attack.assert_not_called()

    def test_no_enemy_walks_to_bush(self):
        context, attack = self.run_style(.9, bushes=[[200, 80, 260, 120]])
        self.assertGreater(context['movement'][0], 0)
        attack.assert_not_called()

    def test_bush_in_gas_is_not_selected(self):
        context, attack = self.run_style(.9, gas=[[60, 60, 140, 140]])
        self.assertIsNone(context['cover'])
        attack.assert_not_called()

    def test_leaving_enemy_is_not_chased(self):
        memory = {'cautious_ambush': {'ambush_until': 11., 'cooldown_until': 16.}}
        context, attack = self.run_style(.9, [[500, 90, 520, 110]], memory)
        self.assertFalse(context['ambushing'])
        self.assertEqual(context['movement'], (0, 0))
        attack.assert_not_called()

    def test_low_hp_without_cover_moves_away(self):
        context, attack = self.run_style(.2, [[190, 90, 210, 110]], bushes=[])
        self.assertLess(context['movement'][0], 0)
        attack.assert_not_called()

    def test_absent_health_bar_is_unknown(self):
        # Health reader rejects scenery / absent bars instead of reporting full HP.
        self.assertIsNone(estimate_player_health(np.zeros((300, 400, 3), dtype=np.uint8), [180, 160, 220, 220], 50))

    def test_health_bar_fill(self):
        for fraction in (.25, .8, 1.):
            frame = np.full((300, 400, 3), 180, dtype=np.uint8)
            frame[125:137, 150:250] = 20
            frame[127:135, 152:152+int(96*fraction)] = [40, 220, 50]
            hp = estimate_player_health(frame, [180, 160, 220, 220], 50)
            self.assertIsNotNone(hp)
            self.assertAlmostEqual(hp, fraction, delta=.03)


if __name__ == '__main__':
    unittest.main()
