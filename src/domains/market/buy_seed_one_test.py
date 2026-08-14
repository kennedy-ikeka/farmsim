"""Tests for buy_seed_one — per-unit seed purchase helper."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_seed_one import buy_seed_one
from src.models.action import BuySeedActionState
from src.models.crops import CROP_CONFIG


def _subjects(env):
    return env.state.farms[0], env.state.privates[0]


class TestBuySeedOne:
    """Tests for `buy_seed_one`."""

    def test_buys_single_seed_at_fixed_cost(self):
        env = _make_env()
        farm, priv = _subjects(env)
        farm.money = 100.0

        cost = CROP_CONFIG["WHEAT"].seed_cost
        ok, occ = buy_seed_one(farm, priv, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5))

        assert ok is True
        assert occ == {"crop": "WHEAT", "count": 1, "unit_cost": cost, "cost": cost}
        assert priv.seeds.WHEAT == 1
        assert farm.money == 100.0 - cost

    def test_accumulates_across_calls(self):
        env = _make_env()
        farm, priv = _subjects(env)
        farm.money = 1000.0
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3)
        cost = CROP_CONFIG["WHEAT"].seed_cost

        results = [buy_seed_one(farm, priv, action) for _ in range(3)]

        assert [r[0] for r in results] == [True, True, True]
        assert priv.seeds.WHEAT == 3
        assert farm.money == 1000.0 - 3 * cost

    def test_noop_when_cannot_afford(self):
        env = _make_env()
        farm, priv = _subjects(env)
        farm.money = 0.0
        cost = CROP_CONFIG["WHEAT"].seed_cost

        ok, occ = buy_seed_one(farm, priv, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1))

        assert ok is False
        assert occ == {"crop": "WHEAT", "count": 0, "unit_cost": cost, "cost": 0}
        assert priv.seeds.WHEAT == 0
        assert farm.money == 0.0

    def test_partial_then_noop_when_money_runs_out(self):
        env = _make_env()
        farm, priv = _subjects(env)
        cost = CROP_CONFIG["WHEAT"].seed_cost
        farm.money = float(cost * 2 + 1)  # afford exactly 2 + a bit
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=10)

        r1 = buy_seed_one(farm, priv, action)
        r2 = buy_seed_one(farm, priv, action)
        r3 = buy_seed_one(farm, priv, action)

        assert r1[0] is True and r2[0] is True
        assert r3[0] is False
        assert priv.seeds.WHEAT == 2

    @pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
    def test_works_for_every_crop(self, crop):
        env = _make_env()
        farm, priv = _subjects(env)
        farm.money = 10_000.0
        cost = CROP_CONFIG[crop].seed_cost

        ok, occ = buy_seed_one(farm, priv, BuySeedActionState(type="BUY_SEED", crop=crop, count=1))

        assert ok is True
        assert occ["unit_cost"] == cost
        assert getattr(priv.seeds, crop) == 1