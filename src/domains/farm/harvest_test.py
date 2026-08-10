import pytest

from tests.fixtures import _make_env
from src.domains.farm.harvest import harvest
from src.models.crops import CROP_CONFIG
from src.models.action import HarvestActionState
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState, AnimalState


def _plant_on_tile(crop="WHEAT", planted_day=0, max_lifespan_step=120,
                   yield_units=1):
    """Build a PlantState pre-placed at the unit's tile with the given fields."""
    return PlantState(
        crop=crop,
        planted_day=planted_day,
        max_lifespan_step=max_lifespan_step,
        yield_units=yield_units,
    )


# ---------------------------------------------------------------------------
# Successful harvest — one-time crops.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop, day, yield_units", [
    ("WHEAT", 2, 1),   # first_yield_day=2
    ("WHEAT", 4, 3),
    ("CARROT", 2, 1),  # first_yield_day=2
    ("MELON", 10, 2),  # first_yield_day=10
])
def test_harvest_one_time_crop_deposits_yield_and_clears_tile(crop, day, yield_units):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=yield_units)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    assert farm.tiles[5][5] is None  # plant consumed
    assert getattr(env.state.private.shed, crop) == yield_units


def test_harvest_one_time_crop_adds_to_existing_shed_stock():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)
    env.state.private.shed.WHEAT = 5

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    assert farm.tiles[5][5] is None
    assert env.state.private.shed.WHEAT == 7


def test_harvest_does_not_touch_other_shed_slots():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)
    env.state.private.shed.CARROT = 4

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    assert env.state.private.shed.WHEAT == 2
    assert env.state.private.shed.CARROT == 4  # untouched


# ---------------------------------------------------------------------------
# Successful harvest — ongoing crops. The plant stays and resets to 0.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop, day", [
    ("TOMATO", 8),      # first_yield_day=8
    ("STRAWBERRY", 10),  # first_yield_day=10
])
def test_harvest_ongoing_crop_deposits_yield_and_keeps_plant(crop, day):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=3)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.crop == crop
    assert tile.yield_units == 0  # reset for next scheduled yield
    assert getattr(env.state.private.shed, crop) == 3


def test_harvest_ongoing_crop_can_harvest_again_later():
    """Two harvests on an ongoing crop each collect accumulated yield."""
    env = _make_env(farmer=(5, 5), day=8)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="TOMATO", planted_day=0, yield_units=2)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert env.state.private.shed.TOMATO == 2
    assert farm.tiles[5][5].yield_units == 0

    # Later, more yield accumulates.
    farm.tiles[5][5].yield_units = 2
    env.state.day = 9
    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert env.state.private.shed.TOMATO == 4


# ---------------------------------------------------------------------------
# first_yield_day gate — harvesting before maturity is a no-op.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop, day", [
    ("WHEAT", 0),
    ("WHEAT", 1),    # first_yield_day=2
    ("CARROT", 1),   # first_yield_day=2
    ("MELON", 9),    # first_yield_day=10
    ("TOMATO", 7),   # first_yield_day=8
    ("STRAWBERRY", 9),  # first_yield_day=10
])
def test_harvest_before_first_yield_day_is_noop(crop, day):
    env = _make_env(farmer=(5, 5), day=day)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop=crop, planted_day=0, yield_units=2)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.yield_units == 2  # untouched
    assert getattr(env.state.private.shed, crop) == 0


def test_harvest_melon_with_yield_before_first_yield_day_is_noop():
    """Melon's watering window starts at day 5, but first_yield_day is 10 —
    a plant with accrued yieldUnits cannot be harvested before day 10."""
    env = _make_env(farmer=(5, 5), day=7)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="MELON", planted_day=0, yield_units=2)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.yield_units == 2
    assert env.state.private.shed.MELON == 0


# ---------------------------------------------------------------------------
# Zero-yield harvest is a no-op (nothing to collect; plant is preserved).
# ---------------------------------------------------------------------------

def test_harvest_one_time_crop_with_zero_yield_is_noop():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=0)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)  # plant not consumed
    assert env.state.private.shed.WHEAT == 0


def test_harvest_ongoing_crop_with_zero_yield_is_noop():
    env = _make_env(farmer=(5, 5), day=8)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="TOMATO", planted_day=0, yield_units=0)

    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.yield_units == 0
    assert env.state.private.shed.TOMATO == 0


# ---------------------------------------------------------------------------
# No-op conditions — tile is not a plant.
# ---------------------------------------------------------------------------

def test_harvest_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert farm.tiles[5][5] is None
    assert env.state.private.shed.WHEAT == 0


def test_harvest_noop_on_locked_tile():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[5][5] = "LOCKED"
    env = _make_env(farmer=(5, 5), day=3, tiles=tiles)
    farm = env.state.farms[0]
    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert farm.tiles[5][5] == "LOCKED"


def test_harvest_noop_on_weed_tile():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = WeedState()
    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert isinstance(farm.tiles[5][5], WeedState)
    assert env.state.private.shed.WHEAT == 0


def test_harvest_noop_on_animal_structure():
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP")
    harvest(env.state, farm, farm.farmer, HarvestActionState(type="HARVEST"))
    assert isinstance(farm.tiles[5][5], AnimalState)


# ---------------------------------------------------------------------------
# Malformed / out-of-bounds positions are silently skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_harvest_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5), day=3)
    farm = env.state.farms[0]
    farm.tiles[5][5] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos
    harvest(env.state, farm, pos, HarvestActionState(type="HARVEST"))
    assert farm.tiles[5][5].yield_units == 2
    assert env.state.private.shed.WHEAT == 0


def test_harvest_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4), day=3)
    farm = env.state.farms[0]
    farm.tiles[4][4] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)
    harvest(env.state, farm, [5, 0], HarvestActionState(type="HARVEST"))
    assert farm.tiles[4][4].yield_units == 2
    assert env.state.private.shed.WHEAT == 0


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches harvest.
# ---------------------------------------------------------------------------

def test_step_dispatches_harvest_action():
    env = _make_env(farmer=(3, 3), day=3)
    farm = env.state.farms[0]
    farm.tiles[3][3] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)

    step = StepState(
        farmer=HarvestActionState(type="HARVEST"),
        hands=[],
        market=[],
    )
    env.step(step)

    assert env.state.farms[0].tiles[3][3] is None
    assert env.state.private.shed.WHEAT == 2


def test_step_harvest_noop_before_maturity_does_not_consume_plant():
    env = _make_env(farmer=(3, 3), day=1)  # before WHEAT first_yield_day=2
    farm = env.state.farms[0]
    farm.tiles[3][3] = _plant_on_tile(crop="WHEAT", planted_day=0, yield_units=2)

    step = StepState(
        farmer=HarvestActionState(type="HARVEST"),
        hands=[],
        market=[],
    )
    env.step(step)

    tile = env.state.farms[0].tiles[3][3]
    assert isinstance(tile, PlantState)
    assert tile.yield_units == 2
    assert env.state.private.shed.WHEAT == 0


# ---------------------------------------------------------------------------
# Sanity: first_yield_day in tests matches CROP_CONFIG.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop, expected", [
    ("WHEAT", 2), ("CARROT", 2), ("TOMATO", 8),
    ("STRAWBERRY", 10), ("MELON", 10),
])
def test_first_yield_day_matches_crop_config(crop, expected):
    assert CROP_CONFIG[crop]["first_yield_day"] == expected