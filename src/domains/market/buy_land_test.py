import pytest

from tests.fixtures import _make_env, _play
from src.domains.market.buy_land import buy_land, QUADRANT_COST, get_valid_buy_land_actions
from src.domains.player.player import Player
from src.models.action import BuyLandActionState, PassActionState
from src.models.environment import StepState
from src.models.farm import WeedState


def _locked_tiles(board=10):
    """Tiles with NW unlocked (None) and NE/SW/SE LOCKED."""
    tiles = [[None] * board for _ in range(board)]
    half = board // 2
    for r in range(board):
        for c in range(board):
            if r >= half or c >= half:  # not NW
                tiles[r][c] = "LOCKED"
    return tiles


def _quadrant_tiles(quadrant, board=10):
    """Return the set of (row, col) positions for a quadrant."""
    half = board // 2
    ranges = {
        "NW": [(r, c) for r in range(0, half) for c in range(0, half)],
        "NE": [(r, c) for r in range(0, half) for c in range(half, board)],
        "SW": [(r, c) for r in range(half, board) for c in range(0, half)],
        "SE": [(r, c) for r in range(half, board) for c in range(half, board)],
    }
    return ranges[quadrant]


class TestBuyLand:
    """Tests for `buy_land`."""

    # ---------------------------------------------------------------------------
    # Successful unlock — fixed order NE -> SW -> SE, increasing cost.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("step_index, quadrant, cumulative_cost", [
        (0, "NE", 1000), (1, "SW", 1000 + 2000), (2, "SE", 1000 + 2000 + 4000),
    ])
    def test_unlocks_quadrants_in_order(self, step_index, quadrant, cumulative_cost):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 10000.0

        for _ in range(step_index + 1):
            buy_land(env.state, BuyLandActionState(type="BUY_LAND"))

        assert quadrant in farm.unlocked_quadrants
        assert farm.money == 10000.0 - cumulative_cost

    def test_unlocks_all_three_in_sequence(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 10000.0

        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))  # NE, $1k
        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))  # SW, $2k
        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))  # SE, $4k

        assert set(farm.unlocked_quadrants) == {"NW", "NE", "SW", "SE"}
        assert farm.money == 10000.0 - (1000 + 2000 + 4000)

    # ---------------------------------------------------------------------------
    # Locked tiles in the unlocked quadrant become None.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("quadrant", ["NE", "SW", "SE"])
    def test_converts_locked_tiles_to_none(self, quadrant):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 10000.0

        # Unlock all quadrants up to and including the target.
        while quadrant not in farm.unlocked_quadrants:
            buy_land(env.state, BuyLandActionState(type="BUY_LAND"))

        for r, c in _quadrant_tiles(quadrant):
            assert farm.tiles[r][c] is None  # was LOCKED, now empty

    def test_does_not_touch_already_unlocked_quadrants(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 10000.0

        # Place a plant in NW (already unlocked) to verify it's untouched.
        farm.tiles[0][0] = "PLANT_MARKER"
        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))  # unlock NE

        assert farm.tiles[0][0] == "PLANT_MARKER"  # NW untouched

    def test_preserves_non_locked_tiles_in_quadrant(self):
        """Tiles in the unlocked quadrant that aren't LOCKED are left as-is."""
        tiles = _locked_tiles()
        marker = WeedState()
        tiles[0][5] = marker  # a non-LOCKED tile in NE quadrant
        env = _make_env(farmer=(4, 4), tiles=tiles)
        farm = env.state.farms[0]
        farm.money = 10000.0

        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))  # unlock NE

        assert isinstance(farm.tiles[0][5], WeedState)  # not a LOCKED tile, untouched

    # ---------------------------------------------------------------------------
    # No-op conditions.
    # ---------------------------------------------------------------------------

    def test_noop_when_cannot_afford(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 500.0  # less than NE cost ($1k)

        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))

        assert farm.unlocked_quadrants == ["NW"]  # nothing unlocked
        assert farm.money == 500.0
        # NE tiles still LOCKED
        assert farm.tiles[0][5] == "LOCKED"

    def test_noop_when_all_quadrants_unlocked(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 10000.0
        farm.unlocked_quadrants = ["NW", "NE", "SW", "SE"]

        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))

        assert farm.money == 10000.0  # no cost
        assert len(farm.unlocked_quadrants) == 4  # unchanged

    def test_exact_money_buys_quadrant(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 1000.0  # exactly NE cost

        buy_land(env.state, BuyLandActionState(type="BUY_LAND"))

        assert "NE" in farm.unlocked_quadrants
        assert farm.money == 0.0


class TestBuyLandDispatch:
    """Integration: buy_land dispatched through `Environment.step`."""

    def test_dispatches_buy_land_action(self):
        env = _make_env(farmer=(4, 4), tiles=_locked_tiles())
        farm = env.state.farms[0]
        farm.money = 5000.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyLandActionState(type="BUY_LAND")],
        )
        _play(env, step)

        assert "NE" in farm.unlocked_quadrants
        assert farm.money == 5000.0 - QUADRANT_COST["NE"]
        assert farm.tiles[0][5] is None  # NE unlocked


class TestGetValidBuyLandActions:
    """Tests for `get_valid_buy_land_actions`."""

    # ---------------------------------------------------------------------------
    # NE is the first buyable quadrant (cost 1000).
    # ---------------------------------------------------------------------------

    def test_no_money_cannot_afford_ne(self):
        player = Player().build(money=0, unlocked_quadrants=["NW"])
        assert get_valid_buy_land_actions(player) == []

    def test_exact_money_buys_ne(self):
        player = Player().build(money=1000, unlocked_quadrants=["NW"])
        actions = get_valid_buy_land_actions(player)
        assert len(actions) == 1
        assert actions[0].type == "BUY_LAND"

    def test_one_short_of_ne(self):
        player = Player().build(money=999, unlocked_quadrants=["NW"])
        assert get_valid_buy_land_actions(player) == []

    # ---------------------------------------------------------------------------
    # SW is next (cost 2000) once NE is unlocked.
    # ---------------------------------------------------------------------------

    def test_cannot_afford_sw(self):
        player = Player().build(money=1000, unlocked_quadrants=["NW", "NE"])
        assert get_valid_buy_land_actions(player) == []

    def test_exact_money_buys_sw(self):
        player = Player().build(money=2000, unlocked_quadrants=["NW", "NE"])
        actions = get_valid_buy_land_actions(player)
        assert len(actions) == 1
        assert actions[0].type == "BUY_LAND"

    # ---------------------------------------------------------------------------
    # All quadrants unlocked — no next quadrant to buy.
    # ---------------------------------------------------------------------------

    def test_all_unlocked_returns_empty(self):
        player = Player().build(money=10000,
                                   unlocked_quadrants=["NW", "NE", "SW", "SE"])
        assert get_valid_buy_land_actions(player) == []

    # ---------------------------------------------------------------------------
    # SE is last (cost 4000) once NW, NE, SW are unlocked.
    # ---------------------------------------------------------------------------

    def test_exact_money_buys_se(self):
        player = Player().build(money=4000,
                                   unlocked_quadrants=["NW", "NE", "SW"])
        actions = get_valid_buy_land_actions(player)
        assert len(actions) == 1
        assert actions[0].type == "BUY_LAND"

    # ---------------------------------------------------------------------------
    # Every returned action has type="BUY_LAND".
    # ---------------------------------------------------------------------------

    def test_each_action_has_type_buy_land(self):
        player = Player().build(money=1000, unlocked_quadrants=["NW"])
        actions = get_valid_buy_land_actions(player)
        for a in actions:
            assert a.type == "BUY_LAND"