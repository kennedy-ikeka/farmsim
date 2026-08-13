"""Tests for the Town controller — shop unlocks + shop/center consumption."""
import random

import pytest

from tests.fixtures import _make_env, _play, _step
from src.domains.environment.town import Town
from src.models.town import (
    ALL_SHOPS,
    SHOP_DEMAND,
    SINGLE_PRODUCT_SHOPS,
    TOWN_CENTER_PRODUCTS,
)
from src.utils.config import (
    TOWN_CENTER_SELL_INTERVAL,
    TOWN_SHOP_SELL_INTERVAL,
    TOWN_SHOP_UNLOCK_INTERVAL,
)


def _rng(seed=0):
    return random.Random(seed)


def _inv(env):
    return env.state.market.inventory


def _town_events(events):
    return [e for e in events if e.player == -1]


def _town_event_types(events):
    return [e.type for e in _town_events(events)]


class TestTown:
    """Tests for `Town` config defaults and custom overrides."""

    def test_defaults_match_config(self):
        town = Town()
        assert town.town_shop_unlock_interval == TOWN_SHOP_UNLOCK_INTERVAL
        assert town.town_shop_sell_interval == TOWN_SHOP_SELL_INTERVAL
        assert town.town_center_sell_interval == TOWN_CENTER_SELL_INTERVAL
        assert town.unlocked_shops == []
        assert town.last_shop_unlock_day == 0
        assert town.last_shop_consume_step == 0
        assert town.last_center_consume_step == 0

    def test_accepts_custom_intervals(self):
        town = Town(town_shop_unlock_interval=1, town_shop_sell_interval=2,
                    town_center_sell_interval=5)
        assert town.town_shop_unlock_interval == 1
        assert town.town_shop_sell_interval == 2
        assert town.town_center_sell_interval == 5


class TestConsume:
    """Tests for `Town.consume` orchestration — runs all three sub-ticks."""

    def test_does_not_advance_step(self):
        env = _make_env(step=4, day=0)
        env.state.town.consume(env.state, _rng())
        assert env.state.step == 4
        assert env.state.day == 0

    def test_runs_all_three_sub_ticks_on_combined_tick(self):
        """At a step where both consume intervals + unlock interval have elapsed,
        all three sub-ticks fire in one consume() call."""
        env = _make_env(step=12, day=3)  # 12 >= shop(4), center(12); 3 >= unlock(3)
        # Pre-seed inventory so we can observe drops.
        for p in ("WHEAT", "EGG", "MILK", "TOMATO", "CARROT", "STRAWBERRY",
                  "MELON", "WOOL"):
            setattr(_inv(env), p, 100)
        _inv(env).FERTILIZER = 100
        n_before = len(env.state.town.unlocked_shops)
        env.state.town.consume(env.state, _rng())
        # A shop was unlocked.
        assert len(env.state.town.unlocked_shops) == n_before + 1
        # last_* markers advanced.
        assert env.state.town.last_shop_unlock_day == 3
        assert env.state.town.last_shop_consume_step == 12
        assert env.state.town.last_center_consume_step == 12


class TestUnlock:
    """Tests for shop unlocks — day-based, random, monotonic, capped."""

    def test_no_unlock_before_interval(self):
        env = _make_env(day=2)
        env.state.town.consume(env.state, _rng())
        assert env.state.town.unlocked_shops == []
        assert env.state.town.last_shop_unlock_day == 0  # unchanged

    def test_fires_on_interval(self):
        env = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)  # day 3
        env.state.town.consume(env.state, _rng())
        assert len(env.state.town.unlocked_shops) == 1
        assert env.state.town.last_shop_unlock_day == TOWN_SHOP_UNLOCK_INTERVAL

    def test_chooses_from_remaining_shops(self):
        env = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)
        env.state.town.consume(env.state, _rng())
        assert env.state.town.unlocked_shops[0] in ALL_SHOPS

    def test_is_deterministic_with_seed(self):
        env1 = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)
        env2 = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)
        env1.state.town.consume(env1.state, _rng(seed=7))
        env2.state.town.consume(env2.state, _rng(seed=7))
        assert env1.state.town.unlocked_shops == env2.state.town.unlocked_shops

    def test_grows_monotonically_and_does_not_repeat(self):
        """Successive unlocks never duplicate and only grow the list."""
        env = _make_env(day=0)
        town = env.state.town
        town.town_shop_unlock_interval = 1  # unlock every day
        seen = set()
        for day in range(1, len(ALL_SHOPS) + 1):
            env.state.day = day
            town.consume(env.state, _rng())
            assert len(town.unlocked_shops) == day
            new_shop = town.unlocked_shops[-1]
            assert new_shop not in seen
            seen.add(new_shop)

    def test_no_unlock_when_all_shops_unlocked(self):
        """Once every shop is unlocked, further unlock ticks are no-ops (no crash)."""
        env = _make_env(day=0)
        town = env.state.town
        town.unlocked_shops = list(ALL_SHOPS)
        town.town_shop_unlock_interval = 1
        env.state.day = 100
        town.consume(env.state, _rng())
        assert town.unlocked_shops == list(ALL_SHOPS)  # unchanged, no duplicate
        assert town.last_shop_unlock_day == 100  # marker still advances

    def test_respects_custom_interval(self):
        env = _make_env(day=5)
        env.state.town.town_shop_unlock_interval = 10
        env.state.town.consume(env.state, _rng())
        assert env.state.town.unlocked_shops == []  # day 5 < 10
        env.state.day = 10
        env.state.town.consume(env.state, _rng())
        assert len(env.state.town.unlocked_shops) == 1


class TestShopConsume:
    """Tests for shop consumption — step-based, per-shop demand, 2x for single-product."""

    def test_no_tick_before_interval(self):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL - 1)  # step 3
        env.state.town.unlocked_shops = ["BAKERY"]
        for p in SHOP_DEMAND["BAKERY"]:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in SHOP_DEMAND["BAKERY"]:
            assert getattr(_inv(env), p) == 100  # unchanged
        assert env.state.town.last_shop_consume_step == 0

    def test_fires_on_interval(self):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)  # step 4
        env.state.town.unlocked_shops = ["BAKERY"]
        for p in SHOP_DEMAND["BAKERY"]:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in SHOP_DEMAND["BAKERY"]:
            assert getattr(_inv(env), p) == 99  # dropped by 1
        assert env.state.town.last_shop_consume_step == TOWN_SHOP_SELL_INTERVAL

    def test_multi_product_drops_one_of_each(self):
        """BAKERY demands EGG + WHEAT; each drops by exactly 1 per tick."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).EGG = 50
        _inv(env).WHEAT = 60
        env.state.town.consume(env.state, _rng())
        assert _inv(env).EGG == 49
        assert _inv(env).WHEAT == 59

    def test_single_product_shop_drops_two(self):
        """YARN_STORE demands WOOL only and consumes 2x per tick."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["YARN_STORE"]
        _inv(env).WOOL = 50
        env.state.town.consume(env.state, _rng())
        assert _inv(env).WOOL == 48  # 50 - 2

    def test_pet_cafe_drops_two_carrots(self):
        """PET_CAFE demands CARROT only and consumes 2x per tick."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["PET_CAFE"]
        _inv(env).CARROT = 50
        env.state.town.consume(env.state, _rng())
        assert _inv(env).CARROT == 48

    @pytest.mark.parametrize("shop", list(SINGLE_PRODUCT_SHOPS))
    def test_all_single_product_shops_consume_2x(self, shop):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = [shop]
        product = SHOP_DEMAND[shop][0]
        setattr(_inv(env), product, 50)
        env.state.town.consume(env.state, _rng())
        assert getattr(_inv(env), product) == 48

    def test_multiple_shops_each_drop_their_demand(self):
        """BAKERY + PIZZA_SHOP both unlocked → each drains its own demand."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY", "PIZZA_SHOP"]
        for p in ("EGG", "WHEAT", "MILK", "TOMATO"):
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        # BAKERY: EGG, WHEAT; PIZZA_SHOP: MILK, TOMATO, WHEAT
        assert _inv(env).EGG == 99       # BAKERY only
        assert _inv(env).MILK == 99       # PIZZA_SHOP only
        assert _inv(env).TOMATO == 99     # PIZZA_SHOP only
        assert _inv(env).WHEAT == 98      # both demand WHEAT → drops by 2

    def test_floors_inventory_at_zero(self):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).WHEAT = 0
        _inv(env).EGG = 0
        env.state.town.consume(env.state, _rng())
        assert _inv(env).WHEAT == 0  # not negative
        assert _inv(env).EGG == 0

    def test_no_shops_unlocked_is_noop(self):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = []
        env.state.town.consume(env.state, _rng())
        # No products drained; marker still advances (the tick "fired" with no shops).
        assert env.state.town.last_shop_consume_step == TOWN_SHOP_SELL_INTERVAL

    def test_respects_custom_interval(self):
        env = _make_env(step=5)
        env.state.town.town_shop_sell_interval = 10
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).WHEAT = 100
        env.state.town.consume(env.state, _rng())
        assert _inv(env).WHEAT == 100  # step 5 < 10
        env.state.step = 10
        env.state.town.consume(env.state, _rng())
        assert _inv(env).WHEAT == 99

    def test_repeated_ticks_accumulate(self):
        """Two consume calls at +interval each drain twice."""
        env = _make_env(step=0)
        town = env.state.town
        town.unlocked_shops = ["BAKERY"]
        town.town_shop_sell_interval = 4
        _inv(env).WHEAT = 100
        env.state.step = 4
        town.consume(env.state, _rng())
        assert _inv(env).WHEAT == 99
        env.state.step = 8
        town.consume(env.state, _rng())
        assert _inv(env).WHEAT == 98


class TestCenterConsume:
    """Tests for town center consumption — step-based, day-scaled, excludes fertilizer."""

    def test_no_tick_before_interval(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL - 1, day=0)  # step 11
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        _inv(env).FERTILIZER = 100
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 100  # unchanged
        assert env.state.town.last_center_consume_step == 0

    def test_fires_on_interval(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)  # step 12
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 99  # day 0 → 1 of each
        assert env.state.town.last_center_consume_step == TOWN_CENTER_SELL_INTERVAL

    def test_excludes_fertilizer(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)
        _inv(env).FERTILIZER = 100
        env.state.town.consume(env.state, _rng())
        assert _inv(env).FERTILIZER == 100  # untouched

    def test_amount_one_through_day_10(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=10)
        # Isolate center: disable shop unlock + shop consume ticks.
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 99  # day 10 still 1

    def test_amount_two_after_day_10(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=11)
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 98  # day 11 → 2

    def test_amount_two_through_day_20(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=20)
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 98  # day 20 still 2

    def test_amount_four_after_day_20(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=21)
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 96  # day 21 → 4

    @pytest.mark.parametrize("day, expected", [(0, 1), (10, 1), (11, 2), (20, 2), (21, 4), (50, 4)])
    def test_amount_scales_with_day(self, day, expected):
        assert Town._center_amount(day) == expected

    def test_floors_inventory_at_zero(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 0)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 0  # not negative

    def test_respects_custom_interval(self):
        env = _make_env(step=5, day=0)
        env.state.town.town_center_sell_interval = 10
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 100  # step 5 < 10
        env.state.step = 10
        env.state.town.consume(env.state, _rng())
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 99

    def test_covers_all_products_except_fertilizer(self):
        """Sanity: TOWN_CENTER_PRODUCTS is exactly the market products minus fertilizer."""
        from src.models.market import MarketInventory
        market_fields = set(MarketInventory.model_fields.keys())
        assert set(TOWN_CENTER_PRODUCTS) == market_fields - {"FERTILIZER"}


class TestTownEvents:
    """Tests for town event recording — emitted by `Town.consume` (player = -1)."""

    def test_no_events_when_no_tick_fires(self):
        env = _make_env(step=0, day=0)
        events = env.state.town.consume(env.state, _rng())
        assert events == []

    def test_no_events_when_inventory_all_zero(self):
        """Center tick fires but drains nothing (all inventory 0) → no event."""
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)
        # Default _make_env market has all inventory at 0; center tick fires but
        # drains nothing.
        events = env.state.town.consume(env.state, _rng())
        assert events == []

    def test_no_shop_consume_event_when_no_shops_unlocked(self):
        """Shop tick fires with no unlocked shops → no event (nothing consumed)."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL, day=0)
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        events = env.state.town.consume(env.state, _rng())
        # Only the center event (day 0, drains 1 each); no shop_consume event.
        assert "SHOP_CONSUME" not in _town_event_types(events)

    def test_shop_unlock_event_recorded_on_unlock(self):
        env = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)
        events = env.state.town.consume(env.state, _rng())
        assert "SHOP_UNLOCK" in _town_event_types(events)
        ev = _town_events(events)[0]
        assert ev.player == -1
        assert ev.type == "SHOP_UNLOCK"
        assert ev.intended == {}
        assert ev.occurred["shop"] in ALL_SHOPS
        assert ev.occurred["shop"] in env.state.town.unlocked_shops
        assert ev.occurred["unlocked_shops"] == env.state.town.unlocked_shops

    def test_shop_unlock_event_step_day_hour_match_state(self):
        env = _make_env(step=5, day=TOWN_SHOP_UNLOCK_INTERVAL)
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.step == 5
        assert ev.day == TOWN_SHOP_UNLOCK_INTERVAL
        assert ev.hour == 5 % 24

    def test_shop_unlock_no_event_when_saturated(self):
        """All shops already unlocked → unlock tick fires but no event emitted."""
        env = _make_env(day=TOWN_SHOP_UNLOCK_INTERVAL)
        env.state.town.unlocked_shops = list(ALL_SHOPS)
        events = env.state.town.consume(env.state, _rng())
        assert "SHOP_UNLOCK" not in _town_event_types(events)

    def test_shop_consume_event_recorded_on_tick(self):
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).EGG = 50
        _inv(env).WHEAT = 50
        events = env.state.town.consume(env.state, _rng())
        types = _town_event_types(events)
        assert "SHOP_CONSUME" in types
        ev = _town_events(events)[types.index("SHOP_CONSUME")]
        assert ev.player == -1
        assert ev.intended == {"shops": ["BAKERY"]}
        assert ev.occurred["consumed"] == {"EGG": 1, "WHEAT": 1}

    def test_shop_consume_event_aggregates_across_shops(self):
        """BAKERY + PIZZA_SHOP both demand WHEAT → consumed WHEAT = 2 in one event."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY", "PIZZA_SHOP"]
        for p in ("EGG", "WHEAT", "MILK", "TOMATO"):
            setattr(_inv(env), p, 100)
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.occurred["consumed"]["WHEAT"] == 2  # BAKERY + PIZZA_SHOP
        assert ev.occurred["consumed"]["EGG"] == 1
        assert ev.occurred["consumed"]["MILK"] == 1
        assert ev.occurred["consumed"]["TOMATO"] == 1
        assert ev.intended["shops"] == ["BAKERY", "PIZZA_SHOP"]

    def test_shop_consume_event_single_product_records_two(self):
        """YARN_STORE consumes 2 WOOL → consumed WOOL = 2 in one event."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["YARN_STORE"]
        _inv(env).WOOL = 50
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.occurred["consumed"] == {"WOOL": 2}

    def test_shop_consume_event_floors_at_actual_inventory(self):
        """Only 1 WHEAT in market, BAKERY demands 1 → consumed WHEAT = 1 (not more)."""
        env = _make_env(step=TOWN_SHOP_SELL_INTERVAL)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).WHEAT = 1
        _inv(env).EGG = 0  # none available
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.occurred["consumed"] == {"WHEAT": 1}  # EGG not in dict (drained 0)
        assert _inv(env).WHEAT == 0
        assert _inv(env).EGG == 0

    def test_center_consume_event_recorded_on_tick(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)
        env.state.town.town_shop_unlock_interval = 10_000  # isolate center
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        events = env.state.town.consume(env.state, _rng())
        types = _town_event_types(events)
        assert "CENTER_CONSUME" in types
        ev = _town_events(events)[types.index("CENTER_CONSUME")]
        assert ev.player == -1
        assert ev.intended == {"day": 0, "amount_per_product": 1}
        assert ev.occurred["consumed"] == {p: 1 for p in TOWN_CENTER_PRODUCTS}

    def test_center_consume_event_records_amount_per_product(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=21)
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.intended == {"day": 21, "amount_per_product": 4}
        assert ev.occurred["consumed"] == {p: 4 for p in TOWN_CENTER_PRODUCTS}

    def test_center_consume_event_excludes_fertilizer(self):
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=0)
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        _inv(env).FERTILIZER = 100
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert "FERTILIZER" not in ev.occurred["consumed"]
        assert _inv(env).FERTILIZER == 100

    def test_center_consume_event_floors_at_actual_inventory(self):
        """Only 1 WHEAT, center wants 4 → consumed WHEAT = 1 (not 4)."""
        env = _make_env(step=TOWN_CENTER_SELL_INTERVAL, day=21)  # amount = 4
        env.state.town.town_shop_unlock_interval = 10_000
        env.state.town.town_shop_sell_interval = 10_000
        _inv(env).WHEAT = 1
        events = env.state.town.consume(env.state, _rng())
        ev = _town_events(events)[0]
        assert ev.occurred["consumed"] == {"WHEAT": 1}  # only what was available

    def test_returns_events_in_unlock_then_shop_then_center_order(self):
        env = _make_env(step=12, day=3)  # all three ticks fire
        env.state.town.unlocked_shops = ["BAKERY"]  # pre-unlock so shop consumes
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        _inv(env).EGG = 50
        _inv(env).WHEAT = 50
        events = env.state.town.consume(env.state, _rng())
        # Unlock fires first (adds another shop), then shop consume, then center.
        types = _town_event_types(events)
        assert types == ["SHOP_UNLOCK", "SHOP_CONSUME", "CENTER_CONSUME"]

    def test_returns_empty_list_when_all_ticks_noop(self):
        """All ticks fire but nothing happens (shops saturated, all inventory 0) → []."""
        env = _make_env(step=12, day=3)  # all intervals elapse
        env.state.town.unlocked_shops = list(ALL_SHOPS)  # saturated → no unlock event
        # All inventory at default 0 → shop/center ticks drain nothing.
        events = env.state.town.consume(env.state, _rng())
        assert events == []


class TestStepDispatch:
    """Integration: town runs inside `Environment.step` between market and time."""

    def test_runs_town_center_consume_on_interval(self):
        """12 PASS steps from a fresh env → town center drains 1 of each product."""
        env = _make_env(step=0, day=0)
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        _inv(env).FERTILIZER = 100
        for s in range(12):
            env.step()
        # After 12 steps, center has ticked once (at step 12, before time advance
        # to step 12... actually: town runs at the current step BEFORE advance,
        # so the 12th step's town runs at step=11, then time advances to 12.
        # Center ticks when step - last >= 12. With last=0, first tick at step 12.
        # After 12 step() calls, step has advanced 0→12, and town ran at steps
        # 0..11 (before each advance). step=11 < 12 → no tick yet.
        # Let's do one more step to reach the tick.
        env.step()  # 13th call: town runs at step=12 → tick!
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 99
        assert _inv(env).FERTILIZER == 100  # untouched

    def test_runs_shop_consume_when_shop_unlocked(self):
        """Pre-unlock BAKERY; after the shop-sell interval, it drains demand."""
        env = _make_env(step=0, day=0)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).EGG = 100
        _inv(env).WHEAT = 100
        # 4 steps → town runs at steps 0..3 (before each advance), no tick yet.
        for _ in range(4):
            env.step()
        # 5th step: town runs at step=4 → shop tick fires.
        env.step()
        assert _inv(env).EGG == 99
        assert _inv(env).WHEAT == 99

    def test_unlocks_shop_on_day_rollover(self):
        """Reaching day 3 (step 72) triggers a shop unlock during town processing."""
        env = _make_env(step=0, day=0)
        # Fast-forward: each step() advances step by 1; town runs before advance.
        # We need town to see day=3. Day advances at step 72 (3 * 24). But town
        # runs BEFORE time advance, so on the step that takes us from step 71 to 72,
        # town sees day=2 (still). The next step (72→73) town sees day=3 → unlock.
        for _ in range(73):
            env.step()
        # town saw day=3 on the 73rd step's town phase.
        assert len(env.state.town.unlocked_shops) == 1
        assert env.state.town.last_shop_unlock_day == 3

    def test_town_runs_between_market_and_time_advance(self):
        """Town consumes at the current step (pre-advance), confirming ordering."""
        env = _make_env(step=11, day=0)  # next step's town runs at step=11
        env.state.town.town_center_sell_interval = 12
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        # This step: town runs at step=11 (< 12, no tick), then time advances to 12.
        env.step()
        assert env.state.step == 12
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 100  # no tick at step 11
        # Next step: town runs at step=12 (>= 12, tick fires), then advances to 13.
        env.step()
        assert env.state.step == 13
        for p in TOWN_CENTER_PRODUCTS:
            assert getattr(_inv(env), p) == 99  # ticked at step 12

    def test_records_center_consume_event(self):
        env = _make_env(step=11, day=0)
        env.state.town.town_center_sell_interval = 12
        for p in TOWN_CENTER_PRODUCTS:
            setattr(_inv(env), p, 100)
        # This step: town runs at step=11 (< 12, no tick), no event.
        env.step()
        assert _town_event_types(env.events) == []
        # Next step: town runs at step=12 (tick), event recorded.
        env.step()
        assert "CENTER_CONSUME" in _town_event_types(env.events)

    def test_records_shop_unlock_event_on_day_rollover(self):
        env = _make_env(step=0, day=0)
        for _ in range(73):
            env.step()
        assert "SHOP_UNLOCK" in _town_event_types(env.events)

    def test_records_shop_consume_event_when_shop_unlocked(self):
        env = _make_env(step=0, day=0)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).EGG = 100
        _inv(env).WHEAT = 100
        for _ in range(4):
            env.step()
        # 5th step: town runs at step=4 → shop tick fires.
        env.step()
        assert "SHOP_CONSUME" in _town_event_types(env.events)

    def test_town_events_carry_player_minus_one(self):
        """All town events recorded by Environment.step have player == -1."""
        env = _make_env(step=0, day=0)
        env.state.town.unlocked_shops = ["BAKERY"]
        _inv(env).EGG = 100
        _inv(env).WHEAT = 100
        for _ in range(13):
            env.step()
        town_events = _town_events(env.events)
        assert town_events  # at least one town event recorded
        for ev in town_events:
            assert ev.player == -1
            assert ev.type in ("SHOP_UNLOCK", "SHOP_CONSUME", "CENTER_CONSUME")

    def test_town_events_do_not_break_player_tagged_events(self):
        """Farm/market player events keep their player tag; town events are -1."""
        from src.models.action import MoveActionState
        from src.models.environment import StepState
        env = _make_env(farmer=(5, 5), players=2)
        _play(env,
            StepState(farmer=MoveActionState(type="NORTH"), hands=[], market=[]),
            StepState(farmer=MoveActionState(type="SOUTH"), hands=[], market=[]),
        )
        move_events = [e for e in env.events if e.type in ("NORTH", "SOUTH")]
        town_events = _town_events(env.events)
        assert [e.player for e in move_events] == [0, 1]  # player-tagged intact
        # No town events at step 0 (no tick fires).
        assert town_events == []