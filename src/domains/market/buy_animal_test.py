import pytest

from tests.fixtures import _make_env
from src.domains.market.buy_animal import buy_animal
from src.models.animals import ANIMAL_CONFIG
from src.models.action import BuyAnimalActionState, PassActionState
from src.models.environment import StepState


@pytest.mark.parametrize("animal", ["GOOSE", "COW", "SHEEP"])
def test_buy_animal_consumes_money_and_adds_to_shed(animal):
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 5000.0
    cost = ANIMAL_CONFIG[animal]["cost"]

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=2))

    assert getattr(env.state.private.shed, animal) == 2
    assert farm.money == 5000.0 - 2 * cost


@pytest.mark.parametrize("animal, expected_cost", [
    ("GOOSE", 300), ("COW", 400), ("SHEEP", 500),
])
def test_buy_animal_uses_fixed_cost(animal, expected_cost):
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 5000.0

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=1))

    assert farm.money == 5000.0 - expected_cost


def test_buy_animal_adds_to_existing_shed_stock():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 5000.0
    env.state.private.shed.GOOSE = 1

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=2))

    assert env.state.private.shed.GOOSE == 3


def test_buy_animal_does_not_touch_other_shed_animals():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 5000.0
    env.state.private.shed.COW = 3

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1))

    assert env.state.private.shed.COW == 3  # untouched


# ---------------------------------------------------------------------------
# Partial fulfillment — only as many as affordable.
# ---------------------------------------------------------------------------

def test_buy_animal_partial_when_cannot_afford_all():
    env = _make_env()
    farm = env.state.farms[0]
    # GOOSE costs 300; 700 money buys 2, not 5.
    farm.money = 700.0

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=5))

    assert env.state.private.shed.GOOSE == 2
    assert farm.money == 100.0  # 700 - 2*300


def test_buy_animal_noop_when_cannot_afford_any():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 200.0  # less than one GOOSE (300)

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1))

    assert env.state.private.shed.GOOSE == 0
    assert farm.money == 200.0


def test_buy_animal_noop_when_zero_money():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 0.0

    buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="COW", count=1))

    assert env.state.private.shed.COW == 0
    assert farm.money == 0.0


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches buy_animal.
# ---------------------------------------------------------------------------

def test_step_dispatches_buy_animal_action():
    env = _make_env()
    farm = env.state.farms[0]
    farm.money = 1000.0

    step = StepState(
        farmer=PassActionState(type="PASS"),
        hands=[],
        market=[BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=2)],
    )
    env.step(step)

    assert env.state.private.shed.GOOSE == 2
    assert farm.money == 1000.0 - 2 * ANIMAL_CONFIG["GOOSE"]["cost"]