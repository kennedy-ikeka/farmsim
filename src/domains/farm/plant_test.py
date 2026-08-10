import pytest

from tests.fixtures import _make_env
from src.domains.farm.plant import plant
from src.models.crops import CROP_CONFIG, TURNS_PER_DAY
from src.models.action import PlantActionState
from src.models.environment import StepState
from src.models.farm import PlantState, WeedState


def _seed_tile():
    """A plant dict as plant() is expected to write one."""
    return None  # placeholder; tests build expected dicts inline


# ---------------------------------------------------------------------------
# Successful planting.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
def test_plant_consumes_one_seed_and_writes_plant_dict(crop):
    env = _make_env(farmer=(5, 5), seeds={crop: 3})
    farm = env.state.farms[0]
    seeds = env.state.private.seeds

    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop=crop))

    assert getattr(seeds, crop) == 2  # one seed consumed
    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    assert tile.kind == "PLANT"
    assert tile.crop == crop
    assert tile.planted_day == 0
    assert tile.watered_today is False
    assert tile.consecutive_unwatered == 0
    assert tile.yield_units == 0
    assert tile.fertilized_until_day == 0


@pytest.mark.parametrize(
    "crop, expected",
    [
        ("WHEAT",      0 + (4 + 1) * TURNS_PER_DAY),
        ("CARROT",     0 + (3 + 1) * TURNS_PER_DAY),
        ("TOMATO",     0 + (11 + 1) * TURNS_PER_DAY),
        ("STRAWBERRY", 0 + (16 + 1) * TURNS_PER_DAY),
        ("MELON",      0 + (10 + 1) * TURNS_PER_DAY),
    ],
)
def test_plant_sets_max_lifespan_step_from_crop_config(crop, expected):
    env = _make_env(farmer=(5, 5), seeds={crop: 1})
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop=crop))
    assert farm.tiles[5][5].max_lifespan_step == expected


def test_plant_max_lifespan_step_offsets_from_current_step():
    """Planting later in the season pushes max_lifespan_step forward."""
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 1}, step=48, day=2)
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    # wheat max_yield_day=4 -> decay at day 7 -> step 48 + 5*24 = 168
    assert farm.tiles[5][5].max_lifespan_step == 48 + (4 + 1) * TURNS_PER_DAY
    assert farm.tiles[5][5].planted_day == 2


def test_plant_only_consumes_one_seed_even_with_many():
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 10})
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert env.state.private.seeds.WHEAT == 9


def test_plant_does_not_touch_other_crops_seeds():
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 2, "CARROT": 5})
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert env.state.private.seeds.WHEAT == 1
    assert env.state.private.seeds.CARROT == 5  # untouched


# ---------------------------------------------------------------------------
# No-op conditions — seed is NOT consumed and no plant is written.
# ---------------------------------------------------------------------------

def test_plant_noop_on_locked_tile():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[5][5] = "LOCKED"
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 2}, tiles=tiles)
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert farm.tiles[5][5] == "LOCKED"  # unchanged
    assert env.state.private.seeds.WHEAT == 2  # seed not consumed


def test_plant_noop_on_occupied_tile():
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 2})
    farm = env.state.farms[0]
    # Pre-place a plant via direct tile mutation.
    farm.tiles[5][5] = PlantState(crop="CARROT", planted_day=0, max_lifespan_step=0)
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert farm.tiles[5][5].crop == "CARROT"  # original plant preserved
    assert env.state.private.seeds.WHEAT == 2  # seed not consumed


def test_plant_noop_when_no_seeds():
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 0})
    farm = env.state.farms[0]
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert farm.tiles[5][5] is None  # nothing planted
    assert env.state.private.seeds.WHEAT == 0


def test_plant_noop_on_weed_tile():
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 2})
    farm = env.state.farms[0]
    farm.tiles[5][5] = WeedState()  # pre-place a weed via direct mutation
    plant(env.state, farm, farm.farmer, PlantActionState(type="PLANT", crop="WHEAT"))
    assert isinstance(farm.tiles[5][5], WeedState)
    assert env.state.private.seeds.WHEAT == 2


# ---------------------------------------------------------------------------
# Malformed / out-of-bounds positions are silently skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_plant_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 2})
    farm = env.state.farms[0]
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos
    plant(env.state, farm, pos, PlantActionState(type="PLANT", crop="WHEAT"))
    assert env.state.private.seeds.WHEAT == 2  # nothing consumed


def test_plant_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4), seeds={"WHEAT": 2})
    farm = env.state.farms[0]
    # position beyond the grid
    plant(env.state, farm, [5, 0], PlantActionState(type="PLANT", crop="WHEAT"))
    # nothing planted anywhere
    for row in farm.tiles:
        assert all(t is None for t in row)
    assert env.state.private.seeds.WHEAT == 2


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches plant.
# ---------------------------------------------------------------------------

def test_step_dispatches_plant_action():
    env = _make_env(farmer=(3, 3), seeds={"WHEAT": 1})
    step = StepState(
        farmer=PlantActionState(type="PLANT", crop="WHEAT"),
        hands=[],
        market=[],
    )
    env.step(step)
    tile = env.state.farms[0].tiles[3][3]
    assert isinstance(tile, PlantState) and tile.kind == "PLANT"
    assert env.state.private.seeds.WHEAT == 0


def test_step_plant_noop_does_not_consume_seed_when_locked():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[5][5] = "LOCKED"
    env = _make_env(farmer=(5, 5), seeds={"WHEAT": 1}, tiles=tiles)
    step = StepState(
        farmer=PlantActionState(type="PLANT", crop="WHEAT"),
        hands=[],
        market=[],
    )
    env.step(step)
    assert env.state.farms[0].tiles[5][5] == "LOCKED"
    assert env.state.private.seeds.WHEAT == 1  # not consumed


# ---------------------------------------------------------------------------
# Sanity: crop config covers every crop in the CROPS literal.
# ---------------------------------------------------------------------------

def test_crop_config_covers_all_crops():
    from src.models.objects import CROPS
    import typing
    # CROPS is a Literal; extract its args.
    crop_args = set(typing.get_args(CROPS))
    assert crop_args == set(CROP_CONFIG.keys())