"""Tests for the Environment controller — step orchestration."""
import pytest

from tests.fixtures import _make_env, _play
from src.domains.environment import Environment
from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.models.action import (
    BuyProductActionState,
    BuySeedActionState,
    HarvestActionState,
    HireActionState,
    MoveActionState,
    PassActionState,
    PlantActionState,
    SellActionState,
    WaterActionState,
)
from src.models.environment import StepState
from src.models.event import EventState
from src.models.farm import PlantState


class TestConstruction:
    """Tests for `Environment` construction — holds the state reference."""

    def test_holds_state(self):
        env = _make_env()
        assert env.state is env.state  # sanity


class TestStep:
    """Tests for `Environment.step` — dispatch and action application order."""

    def test_returns_state(self):
        env = _make_env()
        # A default pass turn (Player.play() returns an all-PASS StepState).
        assert env.step() is env.state

    def test_applies_farmer_action(self):
        env = _make_env(farmer=(5, 5), seeds={"WHEAT": 1})
        step = StepState(
            farmer=PlantActionState(type="PLANT", crop="WHEAT"),
            hands=[],
            market=[],
        )
        _play(env, step)
        assert isinstance(env.state.farms[0].tiles[5][5], PlantState)

    def test_farmer_move_updates_position(self):
        env = _make_env(farmer=(5, 5))
        step = StepState(
            farmer=MoveActionState(type="NORTH"),
            hands=[],
            market=[],
        )
        _play(env, step)
        assert env.state.farms[0].farmer == [4, 5]

    def test_applies_hand_actions_in_order(self):
        env = _make_env(farmer=(4, 4), hands=[[5, 4], [4, 5]], seeds={"WHEAT": 2})
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[
                PlantActionState(type="PLANT", crop="WHEAT"),
                PlantActionState(type="PLANT", crop="WHEAT"),
            ],
            market=[],
        )
        _play(env, step)
        # First hand planted at its position (5,4), second at (4,5).
        assert isinstance(env.state.farms[0].tiles[5][4], PlantState)
        assert isinstance(env.state.farms[0].tiles[4][5], PlantState)
        assert env.state.privates[0].seeds.WHEAT == 0

    def test_missing_hand_action_defaults_to_pass(self):
        env = _make_env(farmer=(4, 4), hands=[[5, 4], [4, 5]], seeds={"WHEAT": 1})
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[PlantActionState(type="PLANT", crop="WHEAT")],  # only 1 action for 2 hands
            market=[],
        )
        _play(env, step)
        # First hand planted at (5,4); second hand PASSed — (4,5) stays empty.
        assert isinstance(env.state.farms[0].tiles[5][4], PlantState)
        assert env.state.farms[0].tiles[4][5] is None

    def test_no_hand_actions_all_pass(self):
        env = _make_env(farmer=(4, 4), hands=[[5, 4], [4, 5]])
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],  # no actions — both hands PASS
            market=[],
        )
        _play(env, step)
        assert env.state.farms[0].tiles[5][4] is None
        assert env.state.farms[0].tiles[4][5] is None

    def test_all_pass_is_noop(self):
        """All-PASS step leaves the farm untouched but advances the time counter."""
        env = _make_env(farmer=(5, 5))
        before = env.state.model_dump()
        step = StepState(farmer=PassActionState(type="PASS"), hands=[], market=[])
        _play(env, step)
        after = env.state.model_dump()
        # Time advances by one turn; everything else is unchanged.
        before["step"] += 1
        before["hour"] += 1
        assert before == after


class TestMarketActions:
    """Tests for market action application and capping in `Environment.step`."""

    def test_applies_market_actions(self):
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 50.0
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[HireActionState(type="HIRE")],
        )
        _play(env, step)
        assert farm_state.hires_today == 1
        assert len(farm_state.hands) == 1

    def test_market_runs_after_farmer_and_hands(self):
        """Farmer plants, a hand waters, then market hires — all in one step."""
        env = _make_env(farmer=(4, 4), hands=[[4, 4]], seeds={"WHEAT": 1})
        farm_state = env.state.farms[0]
        farm_state.money = 50.0
        step = StepState(
            farmer=PlantActionState(type="PLANT", crop="WHEAT"),
            hands=[WaterActionState(type="WATER")],
            market=[HireActionState(type="HIRE")],
        )
        _play(env, step)
        assert isinstance(farm_state.tiles[4][4], PlantState)
        assert farm_state.tiles[4][4].watered_today is True
        assert farm_state.hires_today == 1

    def test_caps_market_actions(self):
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 10_000.0
        # Submit more hires than the cap; only the first MAX should run.
        over_cap = MAX_MARKET_ORDERS_PER_TURN + 5
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[HireActionState(type="HIRE") for _ in range(over_cap)],
        )
        _play(env, step)
        assert farm_state.hires_today == MAX_MARKET_ORDERS_PER_TURN

    def test_exact_cap_market_actions_all_applied(self):
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 10_000.0
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[HireActionState(type="HIRE") for _ in range(MAX_MARKET_ORDERS_PER_TURN)],
        )
        _play(env, step)
        assert farm_state.hires_today == MAX_MARKET_ORDERS_PER_TURN


class TestEvents:
    """Tests for event recording — one Event per applied action."""

    def test_starts_empty(self):
        env = _make_env()
        assert env.events == []

    def test_appends_one_event_per_farmer_action(self):
        env = _make_env(farmer=(5, 5))
        step = StepState(
            farmer=MoveActionState(type="NORTH"),
            hands=[],
            market=[],
        )
        _play(env, step)
        assert len(env.events) == 1
        assert env.events[0].type == "NORTH"

    def test_appends_event_for_each_action_in_dispatch_order(self):
        """farmer -> each hand -> each market action, in that order."""
        env = _make_env(farmer=(4, 4), hands=[[5, 4], [4, 5]], seeds={"WHEAT": 2})
        farm_state = env.state.farms[0]
        farm_state.money = 50.0
        step = StepState(
            farmer=PlantActionState(type="PLANT", crop="WHEAT"),
            hands=[
                PlantActionState(type="PLANT", crop="WHEAT"),
                WaterActionState(type="WATER"),
            ],
            market=[HireActionState(type="HIRE")],
        )
        _play(env, step)
        assert [e.type for e in env.events] == ["PLANT", "PLANT", "WATER", "HIRE"]

    def test_appends_pass_event_for_missing_hand_action(self):
        env = _make_env(farmer=(4, 4), hands=[[5, 4], [4, 5]], seeds={"WHEAT": 1})
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[PlantActionState(type="PLANT", crop="WHEAT")],  # only 1 for 2 hands
            market=[],
        )
        _play(env, step)
        assert [e.type for e in env.events] == ["PASS", "PLANT", "PASS"]

    def test_appends_events_for_market_actions_only_up_to_cap(self):
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 10_000.0
        over_cap = MAX_MARKET_ORDERS_PER_TURN + 5
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[HireActionState(type="HIRE") for _ in range(over_cap)],
        )
        _play(env, step)
        # 1 farmer PASS + 0 hands + cap market actions.
        assert len(env.events) == 1 + MAX_MARKET_ORDERS_PER_TURN
        assert all(e.type == "HIRE" for e in env.events[1:])

    def test_captures_state_context(self):
        env = _make_env(farmer=(4, 4), day=7, step=42)
        env.state.hour = 3
        env.state.player = 0
        step = StepState(
            farmer=MoveActionState(type="NORTH"),
            hands=[],
            market=[],
        )
        _play(env, step)
        e = env.events[0]
        assert e.step == 42
        assert e.day == 7
        assert e.hour == 3
        assert e.player == 0
        assert e.type == "NORTH"

    def test_data_captures_action_parameters(self):
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 500.0
        env.state.market.inventory.FERTILIZER = 50
        env.state.market.prices.FERTILIZER = 100
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=2)],
        )
        _play(env, step)
        # farmer PASS event (empty intended/occurred) + market event with item/count.
        assert env.events[0].intended == {}
        assert env.events[0].occurred == {}
        assert env.events[1].type == "BUY_PRODUCT"
        assert env.events[1].intended == {"item": "FERTILIZER", "count": 2}
        assert env.events[1].occurred == {"item": "FERTILIZER", "count": 2, "price": 100, "cost": 200}

    def test_data_for_sell_includes_item_and_count(self):
        env = _make_env(farmer=(4, 4))
        env.state.privates[0].shed.WHEAT = 5
        env.state.market.prices.WHEAT = 10
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[SellActionState(type="SELL", item="WHEAT", count=2)],
        )
        _play(env, step)
        assert env.events[1].intended == {"item": "WHEAT", "count": 2}
        assert env.events[1].occurred == {"item": "WHEAT", "count": 2, "price": 10, "revenue": 20}

    def test_events_are_event_instances(self):
        env = _make_env(farmer=(5, 5))
        step = StepState(
            farmer=MoveActionState(type="NORTH"),
            hands=[],
            market=[],
        )
        _play(env, step)
        assert all(isinstance(e, EventState) for e in env.events)

    def test_events_accumulate_across_steps(self):
        env = _make_env(farmer=(5, 5))
        step = StepState(
            farmer=MoveActionState(type="NORTH"),
            hands=[],
            market=[],
        )
        _play(env, step)
        _play(env, step)
        assert [e.type for e in env.events] == ["NORTH", "NORTH"]


class TestOccurred:
    """Tests for `occurred` — reflects actual outcome (no-ops and partial fulfillment)."""

    def test_noop_buy_product_with_no_money(self):
        """BUY_PRODUCT requesting 5 with no money: intended counts 5, occurred counts 0."""
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        farm_state.money = 0.0
        env.state.market.inventory.FERTILIZER = 50
        env.state.market.prices.FERTILIZER = 100
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=5)],
        )
        _play(env, step)
        e = env.events[1]
        assert e.intended == {"item": "FERTILIZER", "count": 5}
        assert e.occurred["count"] == 0
        assert e.occurred["cost"] == 0

    def test_partial_fulfillment_buy_product(self):
        """BUY_PRODUCT requesting 5, only 2 affordable: intended 5, occurred 2."""
        env = _make_env(farmer=(4, 4))
        farm_state = env.state.farms[0]
        # 2 units affordable at price 100 (needs 200 money for 2, 300 for 3).
        farm_state.money = 250.0
        env.state.market.inventory.FERTILIZER = 50
        env.state.market.prices.FERTILIZER = 100
        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=5)],
        )
        _play(env, step)
        e = env.events[1]
        assert e.intended == {"item": "FERTILIZER", "count": 5}
        assert e.occurred == {"item": "FERTILIZER", "count": 2, "price": 100, "cost": 200}