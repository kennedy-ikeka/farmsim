import pytest

from tests.fixtures import _make_env, _turn
from src.domains.farm.fertilize import fertilize
from src.domains.farm.water import water
from src.models.action import FertilizeActionState, WaterActionState
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState, AnimalState


def _plant_on_tile(crop="WHEAT", planted_day=0, max_lifespan_step=120,
                   fertilized_until_day=0, yield_units=0):
    return PlantState(
        crop=crop,
        planted_day=planted_day,
        max_lifespan_step=max_lifespan_step,
        fertilized_until_day=fertilized_until_day,
        yield_units=yield_units,
    )


# ---------------------------------------------------------------------------
# Successful fertilize — consumes one fertilizer and sets the 3-day window.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
def test_fertilize_consumes_one_fertilizer_and_sets_window(crop):
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop)
    env.state.privates[0].shed.FERTILIZER = 5

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    tile = farm.tiles[5][5]
    assert tile.fertilized_until_day == 6  # day + 3
    assert env.state.privates[0].shed.FERTILIZER == 4


@pytest.mark.parametrize("day, expected_until", [
    (0, 3), (5, 8), (10, 13), (27, 30),
])
def test_fertilize_window_offsets_from_current_day(day, expected_until):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 1

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5].fertilized_until_day == expected_until


def test_fertilize_with_one_fertilizer_consumes_it_to_zero():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 1

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert env.state.privates[0].shed.FERTILIZER == 0
    assert farm.tiles[5][5].fertilized_until_day == 6


# ---------------------------------------------------------------------------
# Re-fertilizing refreshes the window to a fresh 3 days and consumes again.
# ---------------------------------------------------------------------------

def test_fertilize_refreshes_window_when_already_fertilized():
    env = _make_env(farmer=(5, 5), day=7)
    farm = env.state.farms[0]
    # Previously fertilized at day 5 -> until day 8; still active at day 7.
    farm.tiles[5][5] = _plant_on_tile(fertilized_until_day=8)
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5].fertilized_until_day == 10  # refreshed to day 7 + 3
    assert env.state.privates[0].shed.FERTILIZER == 1


def test_fertilize_refreshes_window_after_expiry():
    env = _make_env(farmer=(5, 5), day=9)
    farm = env.state.farms[0]
    # Fertilization expired at day 8; now day 9.
    farm.tiles[5][5] = _plant_on_tile(fertilized_until_day=8)
    env.state.privates[0].shed.FERTILIZER = 1

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5].fertilized_until_day == 12
    assert env.state.privates[0].shed.FERTILIZER == 0


# ---------------------------------------------------------------------------
# No-op conditions — tile is not a plant, no fertilizer is spent.
# ---------------------------------------------------------------------------

def test_fertilize_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5] is None
    assert env.state.privates[0].shed.FERTILIZER == 2  # not consumed


def test_fertilize_noop_on_locked_tile():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[5][5] = "LOCKED"
    env = _make_env(farmer=(5, 5), day=3, tiles=tiles)
    farm = env.state.farms[0]
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5] == "LOCKED"
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_fertilize_noop_on_weed_tile():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = WeedState()
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert isinstance(farm.tiles[5][5], WeedState)
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_fertilize_noop_on_animal_structure():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP")
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert isinstance(farm.tiles[5][5], AnimalState)
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_fertilize_noop_when_no_fertilizer_in_shed():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(fertilized_until_day=0)
    env.state.privates[0].shed.FERTILIZER = 0

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5].fertilized_until_day == 0  # unchanged
    assert env.state.privates[0].shed.FERTILIZER == 0


# ---------------------------------------------------------------------------
# Malformed / out-of-bounds positions are silently skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_fertilize_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 2
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

    fertilize(env.state, farm, pos, FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[5][5].fertilized_until_day == 0
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_fertilize_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4), day=3)
    farm = env.state.farms[0]
    farm.tiles[4][4] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 2

    fertilize(env.state, farm, [5, 0], FertilizeActionState(type="FERTILIZE"))

    assert farm.tiles[4][4].fertilized_until_day == 0
    assert env.state.privates[0].shed.FERTILIZER == 2


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches fertilize.
# ---------------------------------------------------------------------------

def test_step_dispatches_fertilize_action():
    env = _make_env(farmer=(3, 3), day=4)
    farm = env.state.farms[0]
    farm.tiles[3][3] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 3

    step = StepState(
        farmer=FertilizeActionState(type="FERTILIZE"),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    assert env.state.farms[0].tiles[3][3].fertilized_until_day == 7
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_step_fertilize_noop_without_fertilizer_does_not_set_window():
    env = _make_env(farmer=(3, 3), day=4)
    farm = env.state.farms[0]
    farm.tiles[3][3] = _plant_on_tile()
    env.state.privates[0].shed.FERTILIZER = 0

    step = StepState(
        farmer=FertilizeActionState(type="FERTILIZE"),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    assert env.state.farms[0].tiles[3][3].fertilized_until_day == 0
    assert env.state.privates[0].shed.FERTILIZER == 0


# ---------------------------------------------------------------------------
# Integration with WATER — a fertilized plant earns +2 instead of +1 when
# watered inside the bonus window.
# ---------------------------------------------------------------------------

def test_fertilize_then_water_doubles_watering_bonus():
    env = _make_env(farmer=(5, 5), day=3)  # WHEAT window is [2, 4]
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=0)
    env.state.privates[0].shed.FERTILIZER = 1

    fertilize(env.state, farm, farm.farmer, FertilizeActionState(type="FERTILIZE"))
    assert farm.tiles[5][5].fertilized_until_day == 6

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5].yield_units == 2  # fertilized doubles the +1 bonus


def test_unfertilized_water_in_window_gives_single_bonus():
    """Sanity: the same setup without FERTILIZE gives only +1."""
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=0)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5].yield_units == 1