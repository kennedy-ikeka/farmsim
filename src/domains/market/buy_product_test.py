import pytest

from tests.fixtures import _make_env, _play
from src.domains.market.buy_product import buy_product
from src.models.action import BuyProductActionState, PassActionState
from src.models.environment import StepState


class TestBuyProduct:
    """Tests for `buy_product`."""

    # ---------------------------------------------------------------------------
    # Successful buy — drains market inventory, costs money, fills shed.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("item", ["WHEAT", "FERTILIZER"])
    def test_drains_market_costs_money_fills_shed(self, item):
        env = _make_env()
        farm = env.state.farms[0]
        setattr(env.state.market.inventory, item, 100)
        setattr(env.state.market.prices, item, 25)
        farm.money = 1000.0

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item=item, count=3))

        assert getattr(env.state.market.inventory, item) == 97
        assert farm.money == 925.0
        assert getattr(env.state.privates[0].shed, item) == 3

    def test_adds_to_existing_shed_stock(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 100
        env.state.market.prices.WHEAT = 10
        farm.money = 500.0
        env.state.privates[0].shed.WHEAT = 5

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=2))

        assert env.state.privates[0].shed.WHEAT == 7
        assert env.state.market.inventory.WHEAT == 98
        assert farm.money == 480.0

    # ---------------------------------------------------------------------------
    # Partial fulfillment — limited by market supply and affordability.
    # ---------------------------------------------------------------------------

    def test_partial_when_count_exceeds_market_supply(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 2
        env.state.market.prices.WHEAT = 10
        farm.money = 1000.0

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=5))

        assert env.state.market.inventory.WHEAT == 0  # drained
        assert env.state.privates[0].shed.WHEAT == 2  # only 2 bought
        assert farm.money == 980.0

    def test_partial_when_count_exceeds_affordability(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 100
        env.state.market.prices.WHEAT = 25
        farm.money = 30.0  # 30 // 25 = 1

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=5))

        assert env.state.market.inventory.WHEAT == 99
        assert env.state.privates[0].shed.WHEAT == 1
        assert farm.money == 5.0

    def test_limited_by_both_supply_and_affordability(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 2
        env.state.market.prices.WHEAT = 25
        farm.money = 30.0  # 30 // 25 = 1, but only 2 in stock -> buys 1

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=5))

        assert env.state.privates[0].shed.WHEAT == 1
        assert farm.money == 5.0

    # ---------------------------------------------------------------------------
    # No-op conditions.
    # ---------------------------------------------------------------------------

    def test_noop_when_market_empty(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 0
        env.state.market.prices.WHEAT = 25
        farm.money = 1000.0

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1))

        assert env.state.privates[0].shed.WHEAT == 0
        assert farm.money == 1000.0

    def test_noop_when_no_money(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 100
        env.state.market.prices.WHEAT = 25
        farm.money = 0.0

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1))

        assert env.state.market.inventory.WHEAT == 100
        assert env.state.privates[0].shed.WHEAT == 0
        assert farm.money == 0.0

    def test_noop_when_cannot_afford_one(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.WHEAT = 100
        env.state.market.prices.WHEAT = 25
        farm.money = 10.0  # less than one unit

        buy_product(env.state, BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1))

        assert env.state.market.inventory.WHEAT == 100
        assert env.state.privates[0].shed.WHEAT == 0
        assert farm.money == 10.0


class TestBuyProductDispatch:
    """Integration: buy_product dispatched through `Environment.step`."""

    def test_dispatches_buy_product_action(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.FERTILIZER = 50
        env.state.market.prices.FERTILIZER = 100
        farm.money = 500.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=2)],
        )
        _play(env, step)

        assert env.state.market.inventory.FERTILIZER == 48
        assert env.state.privates[0].shed.FERTILIZER == 2
        assert farm.money == 300.0