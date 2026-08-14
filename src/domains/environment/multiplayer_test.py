"""Multiplayer step orchestration + end-of-day refresh tests."""
import pytest

from tests.fixtures import _make_env, _play, _step
from src.models.action import (
    BuyProductActionState,
    MoveActionState,
    PassActionState,
    PlantActionState,
    SellActionState,
)
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState
from src.utils.config import TURNS_PER_DAY
from src.models.player import InventoryState


class TestStepMultiplayer:
    """Tests for multiplayer step orchestration — both players' farm actions."""

    def test_runs_both_players_farm_actions(self):
        """Player 0 plants at (4,4), player 1 plants at (5,5) in the same step."""
        env = _make_env(farmer=(4, 4), seeds={"WHEAT": 2}, players=2)
        # Give player 1 seeds too.
        env.state.privates[1].seeds.WHEAT = 2
        _play(env,
            StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
            StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
        )
        assert isinstance(env.state.farms[0].tiles[4][4], PlantState)
        assert isinstance(env.state.farms[1].tiles[4][4], PlantState)
        assert env.state.privates[0].seeds.WHEAT == 1
        assert env.state.privates[1].seeds.WHEAT == 1

    def test_events_tagged_with_correct_player(self):
        """Events for player 0 actions have player=0, player 1 actions have player=1."""
        env = _make_env(farmer=(5, 5), players=2)
        _play(env,
            StepState(farmer=MoveActionState(type="NORTH"), hands=[], market=[]),
            StepState(farmer=MoveActionState(type="SOUTH"), hands=[], market=[]),
        )
        # Two move events, one per player.
        assert [e.player for e in env.events] == [0, 1]
        assert [e.type for e in env.events] == ["NORTH", "SOUTH"]

    def test_unscripted_players_pass(self):
        """Scripting only player 0 leaves player 1's farm untouched (a pass plants nothing)."""
        env = _make_env(farmer=(5, 5), seeds={"WHEAT": 1}, players=2)
        _play(env,
            StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
        )
        assert isinstance(env.state.farms[0].tiles[5][5], PlantState)
        # Player 1's tile is untouched (still None).
        assert env.state.farms[1].tiles[5][5] is None

    def test_advances_time(self):
        """Each step() call advances step and hour; day rolls over at TURNS_PER_DAY."""
        env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, day=0, players=2)
        # Plant a crop so we can see end-of-day refresh reset watered_today.
        env.state.farms[0].tiles[5][5] = PlantState(
            crop="WHEAT", planted_day=0, max_lifespan_step=100,
        )
        env.state.farms[0].tiles[5][5].watered_today = True
        _play(env, _step())
        assert env.state.step == TURNS_PER_DAY
        assert env.state.day == 1
        assert env.state.hour == 0
        # End-of-day refresh ran: watered_today reset to False.
        assert env.state.farms[0].tiles[5][5].watered_today is False


class TestMarketInterleave:
    """Tests for market interleaving — round-robin across players, one unit at a time."""

    def test_interleaves_buy_product(self):
        """10 FERTILIZER in market; both players BUY_PRODUCT 10; each gets 5 (fair split)."""
        env = _make_env(farmer=(4, 4), players=2)
        for p in range(2):
            env.state.farms[p].money = 10_000.0
        env.state.market.inventory.FERTILIZER = 10
        env.state.market.prices.FERTILIZER = 10
        _play(env,
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
        )
        assert env.state.privates[0].shed.FERTILIZER == 5
        assert env.state.privates[1].shed.FERTILIZER == 5
        assert env.state.market.inventory.FERTILIZER == 0

    def test_sell_both_players_same_price(self):
        """Both players SELL WHEAT 10 at the same fixed price; both get the same revenue."""
        env = _make_env(farmer=(4, 4), players=2)
        for p in range(2):
            env.state.privates[p].shed.WHEAT = 10
        env.state.market.prices.WHEAT = 25
        _play(env,
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[SellActionState(type="SELL", item="WHEAT", count=10)]),
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[SellActionState(type="SELL", item="WHEAT", count=10)]),
        )
        assert env.state.farms[0].money == 250.0
        assert env.state.farms[1].money == 250.0
        assert env.state.market.inventory.WHEAT == 20

    def test_buy_product_stops_when_one_player_runs_out_of_money(self):
        """Player 0 can afford 3, player 1 can afford 3; 10 in market — each gets 3."""
        env = _make_env(farmer=(4, 4), players=2)
        env.state.market.inventory.FERTILIZER = 10
        env.state.market.prices.FERTILIZER = 100
        for p in range(2):
            env.state.farms[p].money = 300.0  # affords exactly 3
        _play(env,
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
            StepState(farmer=PassActionState(type="PASS"), hands=[],
                       market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
        )
        assert env.state.privates[0].shed.FERTILIZER == 3
        assert env.state.privates[1].shed.FERTILIZER == 3
        assert env.state.market.inventory.FERTILIZER == 4  # 10 - 6


class TestEndOfDay:
    """Tests for end-of-day refresh via `Environment.step` day rollover."""

    def test_unwatered_plant_becomes_weed(self):
        """A plant with consecutive_unwatered=1 not watered today → weed on day rollover."""
        env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, players=2)
        env.state.farms[0].tiles[5][5] = PlantState(
            crop="WHEAT", planted_day=0, max_lifespan_step=100,
        )
        env.state.farms[0].tiles[5][5].consecutive_unwatered = 1
        env.state.farms[0].tiles[5][5].watered_today = False
        _play(env, _step())
        assert isinstance(env.state.farms[0].tiles[5][5], WeedState)

    def test_watered_plant_resets_counter(self):
        """A watered plant survives the day rollover and resets consecutive_unwatered."""
        env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, players=2)
        env.state.farms[0].tiles[5][5] = PlantState(
            crop="WHEAT", planted_day=0, max_lifespan_step=100,
        )
        env.state.farms[0].tiles[5][5].consecutive_unwatered = 1
        env.state.farms[0].tiles[5][5].watered_today = True
        _play(env, _step())
        tile = env.state.farms[0].tiles[5][5]
        assert isinstance(tile, PlantState)
        assert tile.consecutive_unwatered == 0
        assert tile.watered_today is False  # reset for the new day

    def test_hires_reset_and_hands_cleared(self):
        """At day rollover, hires_today resets to 0 and hands are cleared."""
        env = _make_env(farmer=(4, 4), hands=[[5, 4]], step=TURNS_PER_DAY - 1, players=2)
        env.state.farms[0].hires_today = 3
        _play(env, _step())
        assert env.state.farms[0].hires_today == 0
        assert env.state.farms[0].hands == []

    def test_hand_inventory_dropped_to_shed(self):
        """A hand's inventory is dropped into the shed at day rollover; hand is gone."""
        env = _make_env(farmer=(4, 4), hands=[[5, 4]], step=TURNS_PER_DAY - 1, players=2)
        env.state.farms[0].hires_today = 1
        # Give the hand (index 1) some wheat.
        env.state.privates[0].inventories = [InventoryState(), InventoryState(WHEAT=2)]
        _play(env, _step())
        assert env.state.privates[0].shed.WHEAT == 2
        # Inventories truncated to just the farmer's (length 1).
        assert len(env.state.privates[0].inventories) == 1
        assert env.state.farms[0].hands == []

    def test_farmer_keeps_inventory(self):
        """The main farmer's inventory persists across the day rollover."""
        env = _make_env(farmer=(4, 4), step=TURNS_PER_DAY - 1, players=2)
        env.state.privates[0].inventories = [InventoryState(WHEAT=3)]
        _play(env, _step())
        assert env.state.privates[0].inventories[0].WHEAT == 3


class TestStepResult:
    """Tests for `Environment.step_result` and the done flag."""

    def test_returns_per_player_rewards(self):
        """step_result() returns a StepResultState with per-player bank balances."""
        env = _make_env(farmer=(5, 5), players=2)
        env.state.farms[0].money = 100.0
        env.state.farms[1].money = 250.0
        result = env.step_result()
        assert result.reward == {0: 100.0, 1: 250.0}
        assert result.done is False

    def test_done_flag_set_at_episode_end(self):
        """The done flag is set when step reaches EPISODE_STEPS."""
        from src.utils.config import EPISODE_STEPS
        env = _make_env(farmer=(5, 5), step=EPISODE_STEPS - 1, players=2)
        _play(env, _step())
        assert env.done is True
        assert env.state.step == EPISODE_STEPS