import pytest

from tests.fixtures import _make_env, _play
from src.domains.market.buy_seed import buy_seed, get_valid_buy_seed_actions
from src.domains.player.player import Player
from src.models.crops import CROP_CONFIG
from src.models.action import BuySeedActionState, PassActionState
from src.models.environment import StepState


class TestBuySeed:
    """Tests for `buy_seed`."""

    @pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
    def test_consumes_money_and_adds_seeds(self, crop):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0
        cost = CROP_CONFIG[crop]["seed_cost"]

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop=crop, count=3))

        assert farm.money == 1000.0 - 3 * cost
        assert getattr(env.state.privates[0].seeds, crop) == 3

    def test_adds_to_existing_seed_stock(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0
        env.state.privates[0].seeds.WHEAT = 2

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3))

        assert env.state.privates[0].seeds.WHEAT == 5
        assert farm.money == 1000.0 - 3 * CROP_CONFIG["WHEAT"]["seed_cost"]

    def test_does_not_touch_other_crops_seeds(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0
        env.state.privates[0].seeds.CARROT = 5

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=2))

        assert env.state.privates[0].seeds.CARROT == 5  # untouched
        assert env.state.privates[0].seeds.WHEAT == 2

    @pytest.mark.parametrize("crop, expected_cost", [
        ("WHEAT", 10), ("CARROT", 20), ("TOMATO", 50),
        ("STRAWBERRY", 100), ("MELON", 80),
    ])
    def test_uses_fixed_seed_cost(self, crop, expected_cost):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop=crop, count=1))

        assert farm.money == 1000.0 - expected_cost

    # ---------------------------------------------------------------------------
    # Partial fulfillment — only as many as the farm can afford.
    # ---------------------------------------------------------------------------

    def test_partial_fulfillment_when_cannot_afford_all(self):
        env = _make_env()
        farm = env.state.farms[0]
        # WHEAT seed_cost=10; 25 money buys 2 seeds, not 5.
        farm.money = 25.0

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5))

        assert env.state.privates[0].seeds.WHEAT == 2  # only 2 affordable
        assert farm.money == 5.0  # 25 - 2*10 = 5

    def test_exact_money_buys_all(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 30.0  # exactly 3 WHEAT seeds (10 each)

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3))

        assert env.state.privates[0].seeds.WHEAT == 3
        assert farm.money == 0.0

    def test_noop_when_cannot_afford_any(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 5.0  # less than one WHEAT seed (10)

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1))

        assert env.state.privates[0].seeds.WHEAT == 0
        assert farm.money == 5.0  # unchanged

    def test_noop_when_zero_money(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 0.0

        buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1))

        assert env.state.privates[0].seeds.WHEAT == 0
        assert farm.money == 0.0


class TestBuySeedDispatch:
    """Integration: buy_seed dispatched through `Environment.step`."""

    def test_dispatches_buy_seed_action(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 500.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=4)],
        )
        _play(env, step)

        assert env.state.privates[0].seeds.WHEAT == 4
        assert farm.money == 500.0 - 4 * CROP_CONFIG["WHEAT"]["seed_cost"]

    def test_noop_when_broke_does_not_add_seeds(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 0.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1)],
        )
        _play(env, step)

        assert env.state.privates[0].seeds.WHEAT == 0
        assert farm.money == 0.0


class TestGetValidBuySeedActions:
    """Tests for `get_valid_buy_seed_actions`."""

    def test_no_actions_when_broke(self):
        player = Player().build(money=0)
        assert get_valid_buy_seed_actions(player) == []

    def test_only_cheapest_when_minimal_money(self):
        player = Player().build(money=10)
        actions = get_valid_buy_seed_actions(player)
        assert len(actions) == 1
        assert actions[0].crop == "WHEAT"

    def test_all_crops_when_rich(self):
        player = Player().build(money=100)
        actions = get_valid_buy_seed_actions(player)
        assert sorted(a.crop for a in actions) == [
            "CARROT", "MELON", "STRAWBERRY", "TOMATO", "WHEAT",
        ]

    def test_partial_set_at_50(self):
        # 50 >= WHEAT(10), CARROT(20), TOMATO(50) but not STRAWBERRY(100)/MELON(80).
        player = Player().build(money=50)
        actions = get_valid_buy_seed_actions(player)
        assert sorted(a.crop for a in actions) == ["CARROT", "TOMATO", "WHEAT"]

    def test_each_action_has_type_and_count(self):
        player = Player().build(money=100)
        actions = get_valid_buy_seed_actions(player)
        for a in actions:
            assert a.type == "BUY_SEED"
            assert a.count == 1

    def test_crop_field_is_valid(self):
        player = Player().build(money=100)
        actions = get_valid_buy_seed_actions(player)
        valid_crops = set(CROP_CONFIG.keys())
        for a in actions:
            assert a.crop in valid_crops