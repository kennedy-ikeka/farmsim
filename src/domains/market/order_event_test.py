"""Tests for order_event — init_occurred, accumulate, build_event helpers."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.order_event import init_occurred, accumulate, build_event
from src.models.action import (
    BuyAnimalActionState,
    BuyLandActionState,
    BuyProductActionState,
    BuySeedActionState,
    HireActionState,
    SellActionState,
)
from src.models.event import EventState


# ---------------------------------------------------------------------------
# init_occurred — shape per action type.
# ---------------------------------------------------------------------------

def test_init_occurred_sell():
    acc = init_occurred(SellActionState(type="SELL", item="WHEAT", count=10))
    assert acc == {"item": "WHEAT", "count": 0, "price": 0, "revenue": 0.0}


def test_init_occurred_buy_seed():
    from src.models.crops import CROP_CONFIG
    acc = init_occurred(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=10))
    assert acc == {"crop": "WHEAT", "count": 0,
                   "unit_cost": CROP_CONFIG["WHEAT"]["seed_cost"], "cost": 0.0}


def test_init_occurred_buy_product():
    acc = init_occurred(BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10))
    assert acc == {"item": "FERTILIZER", "count": 0, "price": 0, "cost": 0.0}


def test_init_occurred_buy_animal():
    from src.models.animals import ANIMAL_CONFIG
    acc = init_occurred(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=10))
    assert acc == {"animal": "GOOSE", "count": 0,
                   "unit_cost": ANIMAL_CONFIG["GOOSE"]["cost"], "cost": 0.0}


def test_init_occurred_hire():
    acc = init_occurred(HireActionState(type="HIRE"))
    assert acc == {"cost": 0, "position": None, "hired": False}


def test_init_occurred_buy_land():
    acc = init_occurred(BuyLandActionState(type="BUY_LAND"))
    assert acc == {"quadrant": None, "cost": 0, "unlocked": False}


# ---------------------------------------------------------------------------
# accumulate — fold one unit's occurred fragment into the accumulator.
# ---------------------------------------------------------------------------

def test_accumulate_sell_sums_count_and_revenue_and_keeps_latest_price():
    acc = init_occurred(SellActionState(type="SELL", item="WHEAT", count=10))
    accumulate(acc, {"item": "WHEAT", "count": 1, "price": 25, "revenue": 25})
    accumulate(acc, {"item": "WHEAT", "count": 1, "price": 25, "revenue": 25})
    accumulate(acc, {"item": "WHEAT", "count": 1, "price": 30, "revenue": 30})
    assert acc == {"item": "WHEAT", "count": 3, "price": 30, "revenue": 80}


def test_accumulate_buy_seed_sums_count_and_cost():
    from src.models.crops import CROP_CONFIG
    cost = CROP_CONFIG["WHEAT"]["seed_cost"]
    acc = init_occurred(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=10))
    accumulate(acc, {"crop": "WHEAT", "count": 1, "unit_cost": cost, "cost": cost})
    accumulate(acc, {"crop": "WHEAT", "count": 1, "unit_cost": cost, "cost": cost})
    assert acc["count"] == 2
    assert acc["cost"] == 2 * cost
    assert acc["unit_cost"] == cost  # unit_cost stays at the fixed seed cost


def test_accumulate_buy_product_sums_count_and_cost_keeps_latest_price():
    acc = init_occurred(BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10))
    accumulate(acc, {"item": "FERTILIZER", "count": 1, "price": 100, "cost": 100})
    accumulate(acc, {"item": "FERTILIZER", "count": 1, "price": 120, "cost": 120})
    assert acc == {"item": "FERTILIZER", "count": 2, "price": 120, "cost": 220}


def test_accumulate_buy_animal_sums_count_and_cost():
    from src.models.animals import ANIMAL_CONFIG
    cost = ANIMAL_CONFIG["GOOSE"]["cost"]
    acc = init_occurred(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=10))
    accumulate(acc, {"animal": "GOOSE", "count": 1, "unit_cost": cost, "cost": cost})
    accumulate(acc, {"animal": "GOOSE", "count": 1, "unit_cost": cost, "cost": cost})
    assert acc["count"] == 2
    assert acc["cost"] == 2 * cost


def test_accumulate_hire_takes_unit_values_directly():
    acc = init_occurred(HireActionState(type="HIRE"))
    accumulate(acc, {"cost": 1, "position": [5, 4], "hired": True})
    assert acc == {"cost": 1, "position": [5, 4], "hired": True}


def test_accumulate_hire_failed_unit_keeps_zero_cost():
    acc = init_occurred(HireActionState(type="HIRE"))
    accumulate(acc, {"cost": 5, "position": None, "hired": False})
    assert acc == {"cost": 5, "position": None, "hired": False}


def test_accumulate_buy_land_takes_unit_values_directly():
    acc = init_occurred(BuyLandActionState(type="BUY_LAND"))
    accumulate(acc, {"quadrant": "NE", "cost": 1000, "unlocked": True})
    assert acc == {"quadrant": "NE", "cost": 1000, "unlocked": True}


def test_accumulate_buy_land_failed_unit_keeps_quadrant():
    acc = init_occurred(BuyLandActionState(type="BUY_LAND"))
    accumulate(acc, {"quadrant": "NE", "cost": 0, "unlocked": False})
    assert acc == {"quadrant": "NE", "cost": 0, "unlocked": False}


# ---------------------------------------------------------------------------
# accumulate — folds a no-op (failed) unit correctly for counted actions.
# ---------------------------------------------------------------------------

def test_accumulate_sell_failed_unit_does_not_advance_totals():
    acc = init_occurred(SellActionState(type="SELL", item="WHEAT", count=10))
    accumulate(acc, {"item": "WHEAT", "count": 1, "price": 25, "revenue": 25})
    accumulate(acc, {"item": "WHEAT", "count": 0, "price": 0, "revenue": 0})  # shed empty
    assert acc == {"item": "WHEAT", "count": 1, "price": 0, "revenue": 25}


# ---------------------------------------------------------------------------
# build_event — emits a single EventState per order.
# ---------------------------------------------------------------------------

def test_build_event_carries_intended_and_occurred():
    env = _make_env()
    state = env.state
    state.player = 1
    action = SellActionState(type="SELL", item="WHEAT", count=2)
    occurred = {"item": "WHEAT", "count": 2, "price": 25, "revenue": 50}

    ev = build_event(state, action, occurred)

    assert isinstance(ev, EventState)
    assert ev.type == "SELL"
    assert ev.player == 1
    assert ev.intended == {"item": "WHEAT", "count": 2}
    assert ev.occurred == occurred


def test_build_event_step_day_hour_from_state():
    env = _make_env(step=5, day=0)
    state = env.state
    state.player = 0
    action = HireActionState(type="HIRE")

    ev = build_event(state, action, {"cost": 1, "position": None, "hired": False})

    assert ev.step == 5
    assert ev.hour == 5  # step % 24
    assert ev.day == 0


def test_build_event_buy_land():
    env = _make_env()
    state = env.state
    action = BuyLandActionState(type="BUY_LAND")
    occurred = {"quadrant": "NE", "cost": 1000, "unlocked": True}

    ev = build_event(state, action, occurred)

    assert ev.type == "BUY_LAND"
    assert ev.intended == {}
    assert ev.occurred == occurred