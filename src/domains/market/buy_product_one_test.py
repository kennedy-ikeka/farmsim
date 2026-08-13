"""Tests for buy_product_one — per-unit buy-back-from-market helper."""
import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_product_one import buy_product_one
from src.models.action import BuyProductActionState


def _subjects(env):
    return env.state.farms[0], env.state.privates[0], env.state.market


class TestBuyProductOne:
    """Tests for `buy_product_one`."""

    def test_buys_single_unit_at_current_price(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 10
        market.prices.FERTILIZER = 100
        farm.money = 1000.0

        ok, occ = buy_product_one(farm, priv, market,
                                  BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=5))

        assert ok is True
        assert occ == {"item": "FERTILIZER", "count": 1, "price": 100, "cost": 100}
        assert market.inventory.FERTILIZER == 9
        assert priv.shed.FERTILIZER == 1
        assert farm.money == 900.0

    def test_drains_shared_inventory_across_calls(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 3
        market.prices.FERTILIZER = 10
        farm.money = 1000.0
        action = BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)

        results = [buy_product_one(farm, priv, market, action) for _ in range(4)]

        assert [r[0] for r in results] == [True, True, True, False]
        assert market.inventory.FERTILIZER == 0
        assert priv.shed.FERTILIZER == 3
        assert results[3][1] == {"item": "FERTILIZER", "count": 0, "price": 10, "cost": 0}

    def test_noop_when_market_out_of_stock(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 0
        market.prices.FERTILIZER = 10
        farm.money = 1000.0

        ok, occ = buy_product_one(farm, priv, market,
                                  BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=1))

        assert ok is False
        assert occ == {"item": "FERTILIZER", "count": 0, "price": 10, "cost": 0}
        assert farm.money == 1000.0
        assert priv.shed.FERTILIZER == 0

    def test_noop_when_price_non_positive(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 10
        market.prices.FERTILIZER = 0
        farm.money = 1000.0

        ok, occ = buy_product_one(farm, priv, market,
                                  BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=1))

        assert ok is False
        assert occ == {"item": "FERTILIZER", "count": 0, "price": 0, "cost": 0}
        assert market.inventory.FERTILIZER == 10

    def test_noop_when_cannot_afford(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 10
        market.prices.FERTILIZER = 100
        farm.money = 50.0

        ok, occ = buy_product_one(farm, priv, market,
                                  BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=1))

        assert ok is False
        assert occ == {"item": "FERTILIZER", "count": 0, "price": 100, "cost": 0}
        assert market.inventory.FERTILIZER == 10
        assert farm.money == 50.0

    def test_buys_wheat_back_into_shed(self):
        """WHEAT is one of the buyable products (alongside FERTILIZER)."""
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.WHEAT = 5
        market.prices.WHEAT = 20
        farm.money = 100.0

        ok, occ = buy_product_one(farm, priv, market,
                                  BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1))

        assert ok is True
        assert occ == {"item": "WHEAT", "count": 1, "price": 20, "cost": 20}
        assert market.inventory.WHEAT == 4
        assert priv.shed.WHEAT == 1
        assert farm.money == 80.0

    def test_money_runs_out_before_inventory(self):
        env = _make_env()
        farm, priv, market = _subjects(env)
        market.inventory.FERTILIZER = 10
        market.prices.FERTILIZER = 100
        farm.money = 250.0  # affords 2, not 3
        action = BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=10)

        r1 = buy_product_one(farm, priv, market, action)
        r2 = buy_product_one(farm, priv, market, action)
        r3 = buy_product_one(farm, priv, market, action)

        assert r1[0] is True and r2[0] is True
        assert r3[0] is False
        assert priv.shed.FERTILIZER == 2
        assert market.inventory.FERTILIZER == 8
        assert farm.money == 50.0