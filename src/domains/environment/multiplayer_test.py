"""Multiplayer step orchestration + end-of-day refresh tests."""
import pytest

from tests.fixtures import _make_env, _turn, _step
from src.models.action import (
    BuyProductActionState,
    MoveActionState,
    PassActionState,
    PlantActionState,
    SellActionState,
)
from src.models.environment import StepState, TurnActions
from src.models.farm import PlantState, WeedState


# ---------------------------------------------------------------------------
# Both players' farm actions run in a single step.
# ---------------------------------------------------------------------------

def test_step_runs_both_players_farm_actions():
    """Player 0 plants at (4,4), player 1 plants at (5,5) in the same step."""
    env = _make_env(farmer=(4, 4), seeds={"WHEAT": 2}, players=2)
    # Give player 1 seeds too.
    env.state.privates[1].seeds.WHEAT = 2
    payload = TurnActions(actions=[
        StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
        StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
    ])
    env.step(payload)
    assert isinstance(env.state.farms[0].tiles[4][4], PlantState)
    assert isinstance(env.state.farms[1].tiles[4][4], PlantState)
    assert env.state.privates[0].seeds.WHEAT == 1
    assert env.state.privates[1].seeds.WHEAT == 1


def test_step_events_tagged_with_correct_player():
    """Events for player 0 actions have player=0, player 1 actions have player=1."""
    env = _make_env(farmer=(5, 5), players=2)
    payload = TurnActions(actions=[
        StepState(farmer=MoveActionState(type="NORTH"), hands=[], market=[]),
        StepState(farmer=MoveActionState(type="SOUTH"), hands=[], market=[]),
    ])
    env.step(payload)
    # Two move events, one per player.
    assert [e.player for e in env.events] == [0, 1]
    assert [e.type for e in env.events] == ["NORTH", "SOUTH"]


def test_step_fewer_actions_than_players_only_runs_those():
    """A single-action TurnActions only runs player 0; player 1 is skipped."""
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 1}, players=2)
    payload = TurnActions(actions=[
        StepState(farmer=PlantActionState(type="PLANT", crop="WHEAT"), hands=[], market=[]),
    ])
    env.step(payload)
    assert isinstance(env.state.farms[0].tiles[5][5], PlantState)
    # Player 1's tile is untouched (still None).
    assert env.state.farms[1].tiles[5][5] is None


# ---------------------------------------------------------------------------
# Market interleaving — one unit at a time, round-robin across players.
# ---------------------------------------------------------------------------

def test_step_market_interleaves_buy_product():
    """10 FERTILIZER in market; both players BUY_PRODUCT 10; each gets 5 (fair split)."""
    env = _make_env(farmer=(4, 4), players=2)
    for p in range(2):
        env.state.farms[p].money = 10_000.0
    env.state.market.inventory.FERTILIZER = 10
    env.state.market.prices.FERTILIZER = 10
    payload = TurnActions(actions=[
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
    ])
    env.step(payload)
    assert env.state.privates[0].shed.FERTILIZER == 5
    assert env.state.privates[1].shed.FERTILIZER == 5
    assert env.state.market.inventory.FERTILIZER == 0


def test_step_market_sell_both_players_same_price():
    """Both players SELL WHEAT 10 at the same fixed price; both get the same revenue."""
    env = _make_env(farmer=(4, 4), players=2)
    for p in range(2):
        env.state.privates[p].shed.WHEAT = 10
    env.state.market.prices.WHEAT = 25
    payload = TurnActions(actions=[
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[SellActionState(type="SELL", item="WHEAT", count=10)]),
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[SellActionState(type="SELL", item="WHEAT", count=10)]),
    ])
    env.step(payload)
    assert env.state.farms[0].money == 250.0
    assert env.state.farms[1].money == 250.0
    assert env.state.market.inventory.WHEAT == 20


def test_step_market_buy_product_stops_when_one_player_runs_out_of_money():
    """Player 0 can afford 3, player 1 can afford 3; 10 in market — each gets 3."""
    env = _make_env(farmer=(4, 4), players=2)
    env.state.market.inventory.FERTILIZER = 10
    env.state.market.prices.FERTILIZER = 100
    for p in range(2):
        env.state.farms[p].money = 300.0  # affords exactly 3
    payload = TurnActions(actions=[
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
        StepState(farmer=PassActionState(type="PASS"), hands=[],
                   market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)]),
    ])
    env.step(payload)
    assert env.state.privates[0].shed.FERTILIZER == 3
    assert env.state.privates[1].shed.FERTILIZER == 3
    assert env.state.market.inventory.FERTILIZER == 4  # 10 - 6


# ---------------------------------------------------------------------------
# Time advancement.
# ---------------------------------------------------------------------------

def test_step_advances_time():
    """Each step() call advances step and hour; day rolls over at TURNS_PER_DAY."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, day=0, players=2)
    # Plant a crop so we can see end-of-day refresh reset watered_today.
    env.state.farms[0].tiles[5][5] = PlantState(
        crop="WHEAT", planted_day=0, max_lifespan_step=100,
    )
    env.state.farms[0].tiles[5][5].watered_today = True
    env.step(_turn(_step()))
    assert env.state.step == TURNS_PER_DAY
    assert env.state.day == 1
    assert env.state.hour == 0
    # End-of-day refresh ran: watered_today reset to False.
    assert env.state.farms[0].tiles[5][5].watered_today is False


# ---------------------------------------------------------------------------
# End-of-day refresh.
# ---------------------------------------------------------------------------

def test_end_of_day_unwatered_plant_becomes_weed():
    """A plant with consecutive_unwatered=1 not watered today → weed on day rollover."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, players=2)
    env.state.farms[0].tiles[5][5] = PlantState(
        crop="WHEAT", planted_day=0, max_lifespan_step=100,
    )
    env.state.farms[0].tiles[5][5].consecutive_unwatered = 1
    env.state.farms[0].tiles[5][5].watered_today = False
    env.step(_turn(_step()))
    assert isinstance(env.state.farms[0].tiles[5][5], WeedState)


def test_end_of_day_watered_plant_resets_counter():
    """A watered plant survives the day rollover and resets consecutive_unwatered."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(5, 5), step=TURNS_PER_DAY - 1, players=2)
    env.state.farms[0].tiles[5][5] = PlantState(
        crop="WHEAT", planted_day=0, max_lifespan_step=100,
    )
    env.state.farms[0].tiles[5][5].consecutive_unwatered = 1
    env.state.farms[0].tiles[5][5].watered_today = True
    env.step(_turn(_step()))
    tile = env.state.farms[0].tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.consecutive_unwatered == 0
    assert tile.watered_today is False  # reset for the new day


def test_end_of_day_hires_reset_and_hands_cleared():
    """At day rollover, hires_today resets to 0 and hands are cleared."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(4, 4), hands=[[5, 4]], step=TURNS_PER_DAY - 1, players=2)
    env.state.farms[0].hires_today = 3
    env.step(_turn(_step()))
    assert env.state.farms[0].hires_today == 0
    assert env.state.farms[0].hands == []


def test_end_of_day_hand_inventory_dropped_to_shed():
    """A hand's inventory is dropped into the shed at day rollover; hand is gone."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(4, 4), hands=[[5, 4]], step=TURNS_PER_DAY - 1, players=2)
    env.state.farms[0].hires_today = 1
    # Give the hand (index 1) some wheat.
    env.state.privates[0].inventories = [{}, {"WHEAT": 2}]
    env.step(_turn(_step()))
    assert env.state.privates[0].shed.WHEAT == 2
    # Inventories truncated to just the farmer's (length 1).
    assert len(env.state.privates[0].inventories) == 1
    assert env.state.farms[0].hands == []


def test_end_of_day_farmer_keeps_inventory():
    """The main farmer's inventory persists across the day rollover."""
    from src.utils.config import TURNS_PER_DAY
    env = _make_env(farmer=(4, 4), step=TURNS_PER_DAY - 1, players=2)
    env.state.privates[0].inventories = [{"WHEAT": 3}]
    env.step(_turn(_step()))
    assert env.state.privates[0].inventories[0] == {"WHEAT": 3}


def test_step_result_returns_per_player_rewards():
    """step_result() returns a StepResultState with per-player bank balances."""
    env = _make_env(farmer=(5, 5), players=2)
    env.state.farms[0].money = 100.0
    env.state.farms[1].money = 250.0
    result = env.step_result()
    assert result.reward == {0: 100.0, 1: 250.0}
    assert result.done is False


def test_done_flag_set_at_episode_end():
    """The done flag is set when step reaches EPISODE_STEPS."""
    from src.utils.config import EPISODE_STEPS
    env = _make_env(farmer=(5, 5), step=EPISODE_STEPS - 1, players=2)
    env.step(_turn(_step()))
    assert env.done is True
    assert env.state.step == EPISODE_STEPS