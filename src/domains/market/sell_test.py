import pytest

from tests.fixtures import _make_env, _turn
from src.domains.market.sell import sell
from src.models.action import BuySeedActionState, PassActionState, SellActionState
from src.models.environment import StepState


# ---------------------------------------------------------------------------
# Successful sell — moves items from shed to market and credits money.
# ---------------------------------------------------------------------------

def test_sell_moves_items_from_shed_and_credits_money():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    env.state.market.prices.WHEAT = 25

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=3))

    assert env.state.privates[0].shed.WHEAT == 2
    assert env.state.market.inventory.WHEAT == 3
    assert farm.money == 75  # 3 * 25


def test_sell_exact_count_drains_shed_to_zero():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 4
    env.state.market.prices.WHEAT = 10

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=4))

    assert env.state.privates[0].shed.WHEAT == 0
    assert env.state.market.inventory.WHEAT == 4
    assert farm.money == 40


def test_sell_adds_to_existing_market_inventory():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.CARROT = 3
    env.state.market.inventory.CARROT = 10
    env.state.market.prices.CARROT = 35

    sell(env.state, SellActionState(type="SELL", item="CARROT", count=2))

    assert env.state.market.inventory.CARROT == 12  # 10 + 2
    assert farm.money == 70  # 2 * 35


def test_sell_accumulates_money_across_orders():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    env.state.market.prices.WHEAT = 25

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=2))
    assert farm.money == 50

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=3))
    assert farm.money == 125  # 50 + 75


@pytest.mark.parametrize("item", [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
])
def test_sell_works_for_every_sellable_product(item):
    env = _make_env()
    farm = env.state.farms[0]
    setattr(env.state.privates[0].shed, item, 2)
    setattr(env.state.market.prices, item, 5)

    sell(env.state, SellActionState(type="SELL", item=item, count=1))

    assert getattr(env.state.privates[0].shed, item) == 1
    assert getattr(env.state.market.inventory, item) == 1
    assert farm.money == 5


# ---------------------------------------------------------------------------
# Partial fulfillment — sells only what's available in the shed.
# ---------------------------------------------------------------------------

def test_sell_partial_when_count_exceeds_available():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 2
    env.state.market.prices.WHEAT = 25

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=5))

    assert env.state.privates[0].shed.WHEAT == 0  # drained
    assert env.state.market.inventory.WHEAT == 2  # only 2 sold
    assert farm.money == 50  # 2 * 25


def test_sell_does_not_touch_other_shed_items():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    env.state.privates[0].shed.CARROT = 3
    env.state.market.prices.WHEAT = 25

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=2))

    assert env.state.privates[0].shed.CARROT == 3  # untouched
    assert env.state.market.inventory.CARROT == 0  # untouched


# ---------------------------------------------------------------------------
# No-op conditions.
# ---------------------------------------------------------------------------

def test_sell_noop_when_shed_empty():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 0
    env.state.market.prices.WHEAT = 25

    sell(env.state, SellActionState(type="SELL", item="WHEAT", count=1))

    assert env.state.privates[0].shed.WHEAT == 0
    assert env.state.market.inventory.WHEAT == 0
    assert farm.money == 0


def test_sell_noop_on_non_shed_item():
    """Animals (GOOSE/COW/SHEEP) are not in SELLABLE_PRODUCTS, so the action
    model rejects them before sell() is ever reached — verify that here."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SellActionState(type="SELL", item="GOOSE", count=1)


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches sell.
# ---------------------------------------------------------------------------

def test_step_dispatches_sell_action():
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    env.state.market.prices.WHEAT = 25

    step = StepState(
        farmer=PassActionState(type="PASS"),
        hands=[],
        market=[SellActionState(type="SELL", item="WHEAT", count=3)],
    )
    env.step(_turn(step))

    assert env.state.privates[0].shed.WHEAT == 2
    assert env.state.market.inventory.WHEAT == 3
    assert farm.money == 75


def test_step_sell_and_buy_seed_in_same_market_order():
    """Market orders are processed in order — sell first credits money,
    then buy_seed can spend it."""
    env = _make_env()
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    env.state.market.prices.WHEAT = 25
    # WHEAT seed_cost = 10

    step = StepState(
        farmer=PassActionState(type="PASS"),
        hands=[],
        market=[
            SellActionState(type="SELL", item="WHEAT", count=2),   # +50 money
            BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3),  # -30 money
        ],
    )
    env.step(_turn(step))

    assert env.state.privates[0].shed.WHEAT == 3  # 5 - 2 sold
    assert env.state.privates[0].seeds.WHEAT == 3  # 3 seeds bought
    assert farm.money == 20  # 50 - 30