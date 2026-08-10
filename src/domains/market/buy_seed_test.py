import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_seed import buy_seed
from src.models.crops import CROP_CONFIG
from src.models.action import BuySeedActionState, PassActionState
from src.models.environment import StepState


@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
def test_buy_seed_consumes_money_and_adds_seeds(crop):
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 1000.0
    cost = CROP_CONFIG[crop]["seed_cost"]

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop=crop, count=3))

    assert farm.money == 1000.0 - 3 * cost
    assert getattr(env.state.private.seeds, crop) == 3


def test_buy_seed_adds_to_existing_seed_stock():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 1000.0
    env.state.private.seeds.WHEAT = 2

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3))

    assert env.state.private.seeds.WHEAT == 5
    assert farm.money == 1000.0 - 3 * CROP_CONFIG["WHEAT"]["seed_cost"]


def test_buy_seed_does_not_touch_other_crops_seeds():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 1000.0
    env.state.private.seeds.CARROT = 5

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=2))

    assert env.state.private.seeds.CARROT == 5  # untouched
    assert env.state.private.seeds.WHEAT == 2


@pytest.mark.parametrize("crop, expected_cost", [
    ("WHEAT", 10), ("CARROT", 20), ("TOMATO", 50),
    ("STRAWBERRY", 100), ("MELON", 80),
])
def test_buy_seed_uses_fixed_seed_cost(crop, expected_cost):
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 1000.0

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop=crop, count=1))

    assert farm.money == 1000.0 - expected_cost


# ---------------------------------------------------------------------------
# Partial fulfillment — only as many as the farm can afford.
# ---------------------------------------------------------------------------

def test_buy_seed_partial_fulfillment_when_cannot_afford_all():
    env = _make_env()
    farm = env.state.farms[0]
    # WHEAT seed_cost=10; 25 money buys 2 seeds, not 5.
    farm.money = 25.0

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5))

    assert env.state.private.seeds.WHEAT == 2  # only 2 affordable
    assert farm.money == 5.0  # 25 - 2*10 = 5


def test_buy_seed_exact_money_buys_all():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 30.0  # exactly 3 WHEAT seeds (10 each)

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3))

    assert env.state.private.seeds.WHEAT == 3
    assert farm.money == 0.0


def test_buy_seed_noop_when_cannot_afford_any():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 5.0  # less than one WHEAT seed (10)

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1))

    assert env.state.private.seeds.WHEAT == 0
    assert farm.money == 5.0  # unchanged


def test_buy_seed_noop_when_zero_money():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 0.0

    buy_seed(env.state, BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1))

    assert env.state.private.seeds.WHEAT == 0
    assert farm.money == 0.0


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches buy_seed.
# ---------------------------------------------------------------------------

def test_step_dispatches_buy_seed_action():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 500.0

    step = StepState(
        farmer=PassActionState(type="PASS"),
        hands=[],
        market=[BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=4)],
    )
    env.step(step)

    assert env.state.private.seeds.WHEAT == 4
    assert farm.money == 500.0 - 4 * CROP_CONFIG["WHEAT"]["seed_cost"]


def test_step_buy_seed_noop_when_broke_does_not_add_seeds():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 0.0

    step = StepState(
        farmer=PassActionState(type="PASS"),
        hands=[],
        market=[BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1)],
    )
    env.step(step)

    assert env.state.private.seeds.WHEAT == 0
    assert farm.money == 0.0