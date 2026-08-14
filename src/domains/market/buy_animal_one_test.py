"""Tests for buy_animal_one — per-unit animal purchase helper."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_animal_one import buy_animal_one
from src.models.action import BuyAnimalActionState
from src.models.animals import ANIMAL_CONFIG


def _subjects(env):
    return env.state.farms[0], env.state.privates[0]


class TestBuyAnimalOne:
    """Tests for `buy_animal_one`."""

    @pytest.mark.parametrize("animal", ["GOOSE", "COW", "SHEEP"])
    def test_buys_single_animal_at_fixed_cost(self, animal):
        env = _make_env()
        farm, priv = _subjects(env)
        cost = ANIMAL_CONFIG[animal].cost
        farm.money = float(cost) + 100.0

        ok, occ = buy_animal_one(farm, priv, BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=3))

        assert ok is True
        assert occ == {"animal": animal, "count": 1, "unit_cost": cost, "cost": cost}
        assert getattr(priv.shed, animal) == 1
        assert farm.money == float(cost) + 100.0 - cost

    def test_accumulates_across_calls(self):
        env = _make_env()
        farm, priv = _subjects(env)
        cost = ANIMAL_CONFIG["GOOSE"].cost
        farm.money = float(cost) * 3 + 50.0
        action = BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=3)

        results = [buy_animal_one(farm, priv, action) for _ in range(3)]

        assert [r[0] for r in results] == [True, True, True]
        assert priv.shed.GOOSE == 3
        assert farm.money == 50.0

    def test_noop_when_cannot_afford(self):
        env = _make_env()
        farm, priv = _subjects(env)
        cost = ANIMAL_CONFIG["GOOSE"].cost
        farm.money = 0.0

        ok, occ = buy_animal_one(farm, priv, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1))

        assert ok is False
        assert occ == {"animal": "GOOSE", "count": 0, "unit_cost": cost, "cost": 0}
        assert priv.shed.GOOSE == 0
        assert farm.money == 0.0

    def test_partial_then_noop_when_money_runs_out(self):
        env = _make_env()
        farm, priv = _subjects(env)
        cost = ANIMAL_CONFIG["GOOSE"].cost
        farm.money = float(cost) * 2  # afford exactly 2
        action = BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=10)

        r1 = buy_animal_one(farm, priv, action)
        r2 = buy_animal_one(farm, priv, action)
        r3 = buy_animal_one(farm, priv, action)

        assert r1[0] is True and r2[0] is True
        assert r3[0] is False
        assert priv.shed.GOOSE == 2
        assert farm.money == 0.0