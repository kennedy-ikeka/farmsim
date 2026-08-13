"""Tests for the Market controller — dispatch of each market action type."""
import types

import pytest

from tests.fixtures import _make_env
from src.domains.market import Market
from src.models.action import (
    BuyAnimalActionState,
    BuyLandActionState,
    BuyProductActionState,
    BuySeedActionState,
    HireActionState,
    SellActionState,
)
from src.models.animals import ANIMAL_CONFIG
from src.domains.market.buy_land import QUADRANT_COST


class TestMarketApply:
    """Tests for `Market.apply`."""

    # ---------------------------------------------------------------------------
    # The fixture-built market is already a Market controller (IS-A MarketState).
    # ---------------------------------------------------------------------------

    def test_market_in_state_is_market_controller(self):
        env = _make_env()
        assert isinstance(env.state.market, Market)

    # ---------------------------------------------------------------------------
    # SELL dispatches to sell.
    # ---------------------------------------------------------------------------

    def test_sell_dispatches(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 3
        env.state.market.prices.WHEAT = 10
        env.state.market.apply(env.state, SellActionState(type="SELL", item="WHEAT", count=2))
        assert env.state.privates[0].shed.WHEAT == 1
        assert env.state.market.inventory.WHEAT == 2
        assert farm.money == 20.0

    # ---------------------------------------------------------------------------
    # BUY_SEED dispatches to buy_seed.
    # ---------------------------------------------------------------------------

    def test_buy_seed_dispatches(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 100.0
        env.state.market.apply(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=2))
        assert env.state.privates[0].seeds.WHEAT == 2
        assert farm.money < 100.0  # money was spent

    # ---------------------------------------------------------------------------
    # BUY_PRODUCT dispatches to buy_product.
    # ---------------------------------------------------------------------------

    def test_buy_product_dispatches(self):
        env = _make_env()
        farm = env.state.farms[0]
        env.state.market.inventory.FERTILIZER = 50
        env.state.market.prices.FERTILIZER = 100
        farm.money = 500.0
        env.state.market.apply(env.state, BuyProductActionState(type="BUY_PRODUCT", item="FERTILIZER", count=2))
        assert env.state.market.inventory.FERTILIZER == 48
        assert env.state.privates[0].shed.FERTILIZER == 2
        assert farm.money == 300.0

    # ---------------------------------------------------------------------------
    # BUY_ANIMAL dispatches to buy_animal.
    # ---------------------------------------------------------------------------

    def test_buy_animal_dispatches(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0
        env.state.market.apply(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=2))
        assert env.state.privates[0].shed.GOOSE == 2
        assert farm.money == 1000.0 - 2 * ANIMAL_CONFIG["GOOSE"]["cost"]

    # ---------------------------------------------------------------------------
    # HIRE dispatches to hire.
    # ---------------------------------------------------------------------------

    def test_hire_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 50.0
        env.state.market.apply(env.state, HireActionState(type="HIRE"))
        assert farm.hires_today == 1
        assert len(farm.hands) == 1
        assert farm.money == 49.0  # fib(0) = 1

    # ---------------------------------------------------------------------------
    # BUY_LAND dispatches to buy_land.
    # ---------------------------------------------------------------------------

    def test_buy_land_dispatches(self):
        # Use locked tiles so there's something to unlock.
        board = 10
        half = board // 2
        tiles = [[None] * board for _ in range(board)]
        for r in range(board):
            for c in range(board):
                if r >= half or c >= half:
                    tiles[r][c] = "LOCKED"
        env = _make_env(farmer=(4, 4), tiles=tiles)
        farm = env.state.farms[0]
        farm.money = 10000.0
        env.state.market.apply(env.state, BuyLandActionState(type="BUY_LAND"))
        assert "NE" in farm.unlocked_quadrants
        assert farm.money == 10000.0 - QUADRANT_COST["NE"]

    # ---------------------------------------------------------------------------
    # Unsupported action raises ValueError.
    # ---------------------------------------------------------------------------

    def test_unsupported_action_raises(self):
        env = _make_env()
        bogus = types.SimpleNamespace(type="BOGUS")
        with pytest.raises(ValueError, match="Unsupported market action"):
            env.state.market.apply(env.state, bogus)