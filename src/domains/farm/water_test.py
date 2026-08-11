import math

import pytest

from tests.fixtures import _make_env, _turn
from src.domains.farm.water import water
from src.models.crops import CROP_CONFIG
from src.models.action import WaterActionState
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState, AnimalState


def _plant_on_tile(crop="WHEAT", planted_day=0, max_lifespan_step=120,
                   watered_today=False, consecutive_unwatered=1,
                   yield_units=0, fertilized_until_day=0):
    """Build a PlantState pre-placed at (5, 5) with the given fields."""
    return PlantState(
        crop=crop,
        planted_day=planted_day,
        max_lifespan_step=max_lifespan_step,
        watered_today=watered_today,
        consecutive_unwatered=consecutive_unwatered,
        yield_units=yield_units,
        fertilized_until_day=fertilized_until_day,
    )


# ---------------------------------------------------------------------------
# Successful watering — marks the plant and resets the miss counter.
# ---------------------------------------------------------------------------

def test_water_marks_watered_today_and_resets_consecutive_unwatered():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(consecutive_unwatered=2)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    tile = farm.tiles[5][5]
    assert tile.watered_today is True
    assert tile.consecutive_unwatered == 0


@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
def test_water_marks_watered_for_every_crop(crop):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].watered_today is True


# ---------------------------------------------------------------------------
# One-time crops — watering inside the bonus window adds +1 to yield_units,
# or +2 if FERTILIZE's bonus is still active.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "crop, day, expected_bonus",
    [
        # WHEAT: window_start=ceil(4/2)=2, window_end=4
        ("WHEAT", 2, 1),
        ("WHEAT", 3, 1),
        ("WHEAT", 4, 1),
        # CARROT: window_start=ceil(3/2)=2, window_end=3
        ("CARROT", 2, 1),
        ("CARROT", 3, 1),
        # MELON: window_start=ceil(10/2)=5, window_end=10
        ("MELON", 5, 1),
        ("MELON", 10, 1),
    ],
)
def test_water_in_bonus_window_adds_one_to_yield(crop, day, expected_bonus):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=0)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == expected_bonus


@pytest.mark.parametrize(
    "crop, day",
    [
        # WHEAT window is [2, 4]
        ("WHEAT", 0),
        ("WHEAT", 1),
        ("WHEAT", 5),
        ("WHEAT", 6),
        # CARROT window is [2, 3]
        ("CARROT", 1),
        ("CARROT", 4),
        # MELON window is [5, 10]
        ("MELON", 4),
        ("MELON", 11),
    ],
)
def test_water_outside_bonus_window_does_not_add_yield(crop, day):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=0)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == 0
    # but the plant is still marked watered
    assert farm.tiles[5][5].watered_today is True


def test_water_fertilized_in_bonus_window_doubles_bonus():
    """fertilized_until_day >= current day -> +2 instead of +1."""
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    # WHEAT window is [2, 4]; fertilized through day 5
    farm.tiles[5][5] = _plant_on_tile(
        crop="WHEAT", planted_day=0, yield_units=0, fertilized_until_day=5
    )

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == 2


def test_water_fertilized_expired_does_not_double_bonus():
    """fertilized_until_day < current day -> bonus stays at +1."""
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(
        crop="WHEAT", planted_day=0, yield_units=0, fertilized_until_day=2
    )

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == 1


def test_water_accumulates_bonus_across_days():
    """Watering on multiple days in the window stacks the bonus."""
    env = _make_env(farmer=(5, 5), day=2)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=0)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5].yield_units == 1

    # Advance to the next day; the plant must be waterable again.
    env.state.day = 3
    farm.tiles[5][5].watered_today = False
    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5].yield_units == 2


# ---------------------------------------------------------------------------
# Ongoing crops — WATER only marks the plant; the bonus is applied at
# scheduled production time, not here.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop", ["TOMATO", "STRAWBERRY"])
def test_water_on_ongoing_crop_does_not_add_yield(crop):
    env = _make_env(farmer=(5, 5), day=10)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=0)

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == 0
    assert farm.tiles[5][5].watered_today is True


# ---------------------------------------------------------------------------
# One bonus per day — re-watering the same plant on the same day is a no-op.
# ---------------------------------------------------------------------------

def test_water_noop_when_already_watered_today():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(
        crop="WHEAT", planted_day=0, yield_units=1, watered_today=True
    )

    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))

    assert farm.tiles[5][5].yield_units == 1  # no extra bonus
    assert farm.tiles[5][5].watered_today is True


# ---------------------------------------------------------------------------
# No-op conditions — tile is not a plantable plant.
# ---------------------------------------------------------------------------

def test_water_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5] is None


def test_water_noop_on_locked_tile():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[5][5] = "LOCKED"
    env = _make_env(farmer=(5, 5), tiles=tiles)
    farm = env.state.farms[0]
    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert farm.tiles[5][5] == "LOCKED"


def test_water_noop_on_weed_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = WeedState()
    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert isinstance(farm.tiles[5][5], WeedState)


def test_water_noop_on_animal_structure():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP")
    water(env.state, farm, farm.farmer, WaterActionState(type="WATER"))
    assert isinstance(farm.tiles[5][5], AnimalState)
    assert farm.tiles[5][5].kind == "COOP"


# ---------------------------------------------------------------------------
# Malformed / out-of-bounds positions are silently skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_water_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile()
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos
    water(env.state, farm, pos, WaterActionState(type="WATER"))
    assert farm.tiles[5][5].watered_today is False


def test_water_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4))
    farm = env.state.farms[0]
    farm.tiles[4][4] = _plant_on_tile(crop="WHEAT", planted_day=0)
    # position beyond the grid
    water(env.state, farm, [5, 0], WaterActionState(type="WATER"))
    assert farm.tiles[4][4].watered_today is False


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches water.
# ---------------------------------------------------------------------------

def test_step_dispatches_water_action():
    env = _make_env(farmer=(3, 3), day=3)
    farm = env.state.farms[0]
    farm.tiles[3][3] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=0)

    step = StepState(
        farmer=WaterActionState(type="WATER"),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    tile = env.state.farms[0].tiles[3][3]
    assert tile.watered_today is True
    assert tile.yield_units == 1  # day 3 is in the WHEAT window [2, 4]


# ---------------------------------------------------------------------------
# Sanity: bonus window math matches ceil(max_yield_day / 2).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "MELON"])
def test_bonus_window_start_matches_crop_config(crop):
    cfg = CROP_CONFIG[crop]
    assert math.ceil(cfg["max_yield_day"] / 2) == {
        "WHEAT": 2, "CARROT": 2, "MELON": 5,
    }[crop]