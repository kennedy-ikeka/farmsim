"""Tests for buy_land_one — per-unit (single-shot) quadrant-unlock helper."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_land_one import buy_land_one
from src.domains.market.buy_land import QUADRANT_COST, QUADRANT_ORDER
from src.models.action import BuyLandActionState


def _env_with_locked_tiles():
    board = 10
    half = board // 2
    tiles = [[None] * board for _ in range(board)]
    for r in range(board):
        for c in range(board):
            if r >= half or c >= half:
                tiles[r][c] = "LOCKED"
    return _make_env(farmer=(4, 4), tiles=tiles)


def _farm(env):
    return env.state.farms[0]


class TestBuyLandOne:
    """Tests for `buy_land_one`."""

    def test_unlocks_next_quadrant_in_order(self):
        env = _env_with_locked_tiles()
        farm = _farm(env)
        farm.money = 10_000.0

        ok, occ = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))

        assert ok is True
        assert occ == {"quadrant": "NE", "cost": QUADRANT_COST["NE"], "unlocked": True}
        assert "NE" in farm.unlocked_quadrants
        assert farm.money == 10_000.0 - QUADRANT_COST["NE"]
        # NE quadrant's LOCKED tiles are now None.
        half = 10 // 2
        assert farm.tiles[0][half] is None  # was LOCKED, now empty

    def test_unlocks_in_sequence_across_calls(self):
        env = _env_with_locked_tiles()
        farm = _farm(env)
        farm.money = 10_000.0

        r1 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))
        r2 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))
        r3 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))
        r4 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))

        assert [r[1]["quadrant"] for r in (r1, r2, r3)] == ["NE", "SW", "SE"]
        assert all(r[0] for r in (r1, r2, r3))
        # All quadrants unlocked — next attempt is a no-op.
        assert r4 == (False, {"quadrant": None, "cost": 0, "unlocked": False})

    def test_noop_when_all_quadrants_unlocked(self):
        env = _env_with_locked_tiles()
        farm = _farm(env)
        farm.unlocked_quadrants = ["NW", "NE", "SW", "SE"]
        farm.money = 10_000.0

        ok, occ = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))

        assert ok is False
        assert occ == {"quadrant": None, "cost": 0, "unlocked": False}
        assert farm.money == 10_000.0

    def test_noop_when_cannot_afford(self):
        env = _env_with_locked_tiles()
        farm = _farm(env)
        farm.money = 0.0

        ok, occ = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))

        assert ok is False
        assert occ == {"quadrant": "NE", "cost": 0, "unlocked": False}
        assert "NE" not in farm.unlocked_quadrants
        assert farm.money == 0.0

    def test_partial_then_noop_when_money_runs_out(self):
        env = _env_with_locked_tiles()
        farm = _farm(env)
        # Afford NE (1000) only.
        farm.money = float(QUADRANT_COST["NE"])

        r1 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))
        r2 = buy_land_one(farm, BuyLandActionState(type="BUY_LAND"))

        assert r1[0] is True
        assert r2[0] is False
        assert "NE" in farm.unlocked_quadrants
        assert "SW" not in farm.unlocked_quadrants
        assert farm.money == 0.0