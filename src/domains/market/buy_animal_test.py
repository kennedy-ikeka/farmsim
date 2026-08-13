import pytest

from tests.fixtures import _make_env, _play
from src.domains.market.buy_animal import buy_animal
from src.models.animals import ANIMAL_CONFIG
from src.models.action import BuyAnimalActionState, PassActionState
from src.models.environment import StepState


class TestBuyAnimal:
    """Tests for `buy_animal`."""

    @pytest.mark.parametrize("animal", ["GOOSE", "COW", "SHEEP"])
    def test_consumes_money_and_adds_to_shed(self, animal):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 5000.0
        cost = ANIMAL_CONFIG[animal]["cost"]

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=2))

        assert getattr(env.state.privates[0].shed, animal) == 2
        assert farm.money == 5000.0 - 2 * cost

    @pytest.mark.parametrize("animal, expected_cost", [
        ("GOOSE", 300), ("COW", 400), ("SHEEP", 500),
    ])
    def test_uses_fixed_cost(self, animal, expected_cost):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 5000.0

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal=animal, count=1))

        assert farm.money == 5000.0 - expected_cost

    def test_adds_to_existing_shed_stock(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 5000.0
        env.state.privates[0].shed.GOOSE = 1

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=2))

        assert env.state.privates[0].shed.GOOSE == 3

    def test_does_not_touch_other_shed_animals(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 5000.0
        env.state.privates[0].shed.COW = 3

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1))

        assert env.state.privates[0].shed.COW == 3  # untouched

    # ---------------------------------------------------------------------------
    # Partial fulfillment — only as many as affordable.
    # ---------------------------------------------------------------------------

    def test_partial_when_cannot_afford_all(self):
        env = _make_env()
        farm = env.state.farms[0]
        # GOOSE costs 300; 700 money buys 2, not 5.
        farm.money = 700.0

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=5))

        assert env.state.privates[0].shed.GOOSE == 2
        assert farm.money == 100.0  # 700 - 2*300

    def test_noop_when_cannot_afford_any(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 200.0  # less than one GOOSE (300)

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1))

        assert env.state.privates[0].shed.GOOSE == 0
        assert farm.money == 200.0

    def test_noop_when_zero_money(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 0.0

        buy_animal(env.state, BuyAnimalActionState(type="BUY_ANIMAL", animal="COW", count=1))

        assert env.state.privates[0].shed.COW == 0
        assert farm.money == 0.0


class TestBuyAnimalDispatch:
    """Integration: buy_animal dispatched through `Environment.step`."""

    def test_dispatches_buy_animal_action(self):
        env = _make_env()
        farm = env.state.farms[0]
        farm.money = 1000.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=2)],
        )
        _play(env, step)

        assert env.state.privates[0].shed.GOOSE == 2
        assert farm.money == 1000.0 - 2 * ANIMAL_CONFIG["GOOSE"]["cost"]