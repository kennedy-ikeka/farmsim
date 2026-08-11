"""Tests for sell_one — per-unit sell helper used by the market interleave loop."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.sell_one import sell_one
from src.models.action import SellActionState


def _subjects(env):
    return env.state.farms[0], env.state.privates[0], env.state.market


# ---------------------------------------------------------------------------
# Successful single-unit sell.
# ---------------------------------------------------------------------------

def test_sell_one_moves_one_unit_and_credits_price():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 5
    market.prices.WHEAT = 25

    ok, occ = sell_one(farm, priv, market, SellActionState(type="SELL", item="WHEAT", count=10))

    assert ok is True
    assert occ == {"item": "WHEAT", "count": 1, "price": 25, "revenue": 25}
    assert priv.shed.WHEAT == 4
    assert market.inventory.WHEAT == 1
    assert farm.money == 25


def test_sell_one_adds_to_existing_market_inventory():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.CARROT = 2
    market.inventory.CARROT = 10
    market.prices.CARROT = 35

    ok, _ = sell_one(farm, priv, market, SellActionState(type="SELL", item="CARROT", count=1))

    assert ok is True
    assert market.inventory.CARROT == 11
    assert farm.money == 35


def test_sell_one_drains_last_unit():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 1
    market.prices.WHEAT = 10

    ok, _ = sell_one(farm, priv, market, SellActionState(type="SELL", item="WHEAT", count=1))

    assert ok is True
    assert priv.shed.WHEAT == 0
    assert market.inventory.WHEAT == 1
    assert farm.money == 10


# ---------------------------------------------------------------------------
# No-op conditions — returns (False, zeroed occurred).
# ---------------------------------------------------------------------------

def test_sell_one_noop_when_shed_empty():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 0
    market.prices.WHEAT = 25

    ok, occ = sell_one(farm, priv, market, SellActionState(type="SELL", item="WHEAT", count=1))

    assert ok is False
    assert occ == {"item": "WHEAT", "count": 0, "price": 0, "revenue": 0}
    assert priv.shed.WHEAT == 0
    assert market.inventory.WHEAT == 0
    assert farm.money == 0


def test_sell_one_noop_when_price_non_positive():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 5
    market.prices.WHEAT = 0

    ok, occ = sell_one(farm, priv, market, SellActionState(type="SELL", item="WHEAT", count=1))

    assert ok is False
    assert occ == {"item": "WHEAT", "count": 0, "price": 0, "revenue": 0}
    assert priv.shed.WHEAT == 5  # shed untouched
    assert farm.money == 0


# ---------------------------------------------------------------------------
# Repeated calls accumulate — model the interleave loop's behavior.
# ---------------------------------------------------------------------------

def test_sell_one_called_repeatedly_drains_shed_and_accumulates_money():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 3
    market.prices.WHEAT = 10
    action = SellActionState(type="SELL", item="WHEAT", count=3)

    results = [sell_one(farm, priv, market, action) for _ in range(3)]

    assert [r[0] for r in results] == [True, True, True]
    assert priv.shed.WHEAT == 0
    assert market.inventory.WHEAT == 3
    assert farm.money == 30
    # 4th call is a no-op (shed empty).
    ok, occ = sell_one(farm, priv, market, action)
    assert ok is False
    assert occ["count"] == 0


@pytest.mark.parametrize("item", [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
])
def test_sell_one_works_for_every_sellable_product(item):
    env = _make_env()
    farm, priv, market = _subjects(env)
    setattr(priv.shed, item, 2)
    setattr(market.prices, item, 5)

    ok, occ = sell_one(farm, priv, market, SellActionState(type="SELL", item=item, count=1))

    assert ok is True
    assert occ == {"item": item, "count": 1, "price": 5, "revenue": 5}
    assert getattr(priv.shed, item) == 1
    assert farm.money == 5


def test_sell_one_does_not_touch_other_shed_items():
    env = _make_env()
    farm, priv, market = _subjects(env)
    priv.shed.WHEAT = 5
    priv.shed.CARROT = 3
    market.prices.WHEAT = 25

    sell_one(farm, priv, market, SellActionState(type="SELL", item="WHEAT", count=1))

    assert priv.shed.CARROT == 3
    assert market.inventory.CARROT == 0