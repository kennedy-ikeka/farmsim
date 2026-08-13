"""Tests for hire_one — per-unit (single-shot) farm-hand hire helper."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.hire_one import hire_one
from src.domains.market.hire import _fib
from src.models.action import HireActionState


def _farm(env):
    return env.state.farms[0]


class TestHireOne:
    """Tests for `hire_one`."""

    @pytest.mark.parametrize("hires_so_far, expected_cost", [
        (0, 1), (1, 1), (2, 2), (3, 3), (4, 5), (5, 8),
    ])
    def test_charges_escalating_fib_cost(self, hires_so_far, expected_cost):
        env = _make_env(farmer=(4, 4))
        farm = _farm(env)
        farm.money = 1000.0
        farm.hires_today = hires_so_far

        ok, occ = hire_one(farm, HireActionState(type="HIRE"))

        assert ok is True
        assert occ == {"cost": expected_cost, "position": farm.hands[-1], "hired": True}
        assert farm.money == 1000.0 - expected_cost
        assert farm.hires_today == hires_so_far + 1
        assert len(farm.hands) == 1

    def test_noop_when_cannot_afford(self):
        env = _make_env(farmer=(4, 4))
        farm = _farm(env)
        farm.money = 0.0

        ok, occ = hire_one(farm, HireActionState(type="HIRE"))

        assert ok is False
        assert occ == {"cost": _fib(0), "position": None, "hired": False}
        assert farm.hires_today == 0
        assert farm.hands == []
        assert farm.money == 0.0

    def test_escalates_across_calls(self):
        env = _make_env(farmer=(4, 4))
        farm = _farm(env)
        farm.money = 100.0

        r1 = hire_one(farm, HireActionState(type="HIRE"))  # cost 1
        r2 = hire_one(farm, HireActionState(type="HIRE"))  # cost 1
        r3 = hire_one(farm, HireActionState(type="HIRE"))  # cost 2

        assert r1[0] is True and r2[0] is True and r3[0] is True
        assert farm.hires_today == 3
        assert len(farm.hands) == 3
        assert farm.money == 100.0 - (1 + 1 + 2)

    def test_spawns_at_shed_adjacent_tile(self):
        env = _make_env(farmer=(4, 4))
        farm = _farm(env)
        farm.money = 100.0

        ok, occ = hire_one(farm, HireActionState(type="HIRE"))

        assert ok is True
        # First free center tile in NWSE order with farmer at (4,4) is (5,4).
        assert occ["position"] == [5, 4]