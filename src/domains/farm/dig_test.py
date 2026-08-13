import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.dig import dig
from src.models.action import DigActionState
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState, AnimalState


class TestDig:
    """Tests for `dig`."""

    # ---------------------------------------------------------------------------
    # Successful dig — clears a plant, weed, or empty animal structure.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
    def test_clears_plant(self, crop):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = PlantState(crop=crop, planted_day=0, max_lifespan_step=120)

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        assert farm.tiles[5][5] is None

    def test_clears_weed(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = WeedState()

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        assert farm.tiles[5][5] is None

    @pytest.mark.parametrize("kind", ["COOP", "PASTURE"])
    def test_clears_empty_animal_structure(self, kind):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind=kind)  # no animal housed

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        assert farm.tiles[5][5] is None

    # ---------------------------------------------------------------------------
    # No-op on a structure that houses an animal — cannot be dug.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("kind, animal", [
        ("COOP", "GOOSE"),
        ("PASTURE", "COW"),
        ("PASTURE", "SHEEP"),
    ])
    def test_noop_on_structure_with_animal(self, kind, animal):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind=kind, animal=animal)

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        tile = farm.tiles[5][5]
        assert isinstance(tile, AnimalState)
        assert tile.animal == animal
        assert tile.kind == kind

    # ---------------------------------------------------------------------------
    # No-op conditions — nothing to dig.
    # ---------------------------------------------------------------------------

    def test_noop_on_empty_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        dig(farm, farm.farmer, DigActionState(type="DIG"))
        assert farm.tiles[5][5] is None

    def test_noop_on_locked_tile(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = "LOCKED"
        env = _make_env(farmer=(5, 5), tiles=tiles)
        farm = env.state.farms[0]
        dig(farm, farm.farmer, DigActionState(type="DIG"))
        assert farm.tiles[5][5] == "LOCKED"

    # ---------------------------------------------------------------------------
    # Digging a plant does not deposit yield into the shed.
    # ---------------------------------------------------------------------------

    def test_plant_does_not_yield_produce(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = PlantState(
            crop="WHEAT", planted_day=0, max_lifespan_step=120, yield_units=4
        )
        env.state.privates[0].shed.WHEAT = 0

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        assert farm.tiles[5][5] is None
        assert env.state.privates[0].shed.WHEAT == 0  # no produce from digging

    def test_does_not_touch_other_tiles(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = WeedState()
        farm.tiles[5][4] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        farm.tiles[4][5] = AnimalState(kind="COOP")

        dig(farm, farm.farmer, DigActionState(type="DIG"))

        assert farm.tiles[5][5] is None
        assert isinstance(farm.tiles[5][4], PlantState)  # untouched
        assert isinstance(farm.tiles[4][5], AnimalState)  # untouched

    # ---------------------------------------------------------------------------
    # Malformed / out-of-bounds positions are silently skipped.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = WeedState()
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos
        dig(farm, pos, DigActionState(type="DIG"))
        assert isinstance(farm.tiles[5][5], WeedState)  # untouched

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = WeedState()
        dig(farm, [5, 0], DigActionState(type="DIG"))
        assert isinstance(farm.tiles[4][4], WeedState)


class TestDigDispatch:
    """Integration: dig actions dispatched through `Environment.step` reach `dig`."""

    def test_dispatches_dig_action_on_plant(self):
        env = _make_env(farmer=(3, 3))
        farm = env.state.farms[0]
        farm.tiles[3][3] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)

        step = StepState(
            farmer=DigActionState(type="DIG"),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.farms[0].tiles[3][3] is None

    def test_dispatches_dig_action_on_weed(self):
        env = _make_env(farmer=(3, 3))
        farm = env.state.farms[0]
        farm.tiles[3][3] = WeedState()

        step = StepState(
            farmer=DigActionState(type="DIG"),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.farms[0].tiles[3][3] is None

    def test_dig_noop_on_structure_with_animal(self):
        env = _make_env(farmer=(3, 3))
        farm = env.state.farms[0]
        farm.tiles[3][3] = AnimalState(kind="COOP", animal="GOOSE")

        step = StepState(
            farmer=DigActionState(type="DIG"),
            hands=[],
            market=[],
        )
        _play(env, step)

        tile = env.state.farms[0].tiles[3][3]
        assert isinstance(tile, AnimalState)
        assert tile.animal == "GOOSE"