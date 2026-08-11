"""Tests for Farm.refresh_tiles — per-tile end-of-day refresh dispatch.

`refresh_plant` and `refresh_animal` have their own dedicated tests; these
tests focus on the dispatch the `Farm.refresh_tiles(state)` method does:
route each tile to the right per-tile refresh, leave None / WeedState / LOCKED
tiles untouched, and handle empty / mixed grids.
"""
import pytest

from tests.fixtures import _make_env
from src.domains.farm import Farm
from src.models.farm import AnimalState, PlantState, WeedState


def _plant(consecutive_unwatered=0, watered_today=False, max_lifespan_step=100,
           yield_units=0, crop="WHEAT", planted_day=0):
    return PlantState(
        crop=crop, planted_day=planted_day,
        max_lifespan_step=max_lifespan_step,
        consecutive_unwatered=consecutive_unwatered,
        watered_today=watered_today,
        yield_units=yield_units,
    )


def _structure(kind="COOP", animal="GOOSE", fed_today=False, consecutive_unfed=0):
    return AnimalState(kind=kind, animal=animal, fed_today=fed_today,
                       consecutive_unfed=consecutive_unfed)


def _farm(env, p=0):
    return env.state.farms[p]


# ---------------------------------------------------------------------------
# IS-A FarmState — the controller carries refresh_tiles.
# ---------------------------------------------------------------------------

def test_farm_in_state_is_farm_controller():
    env = _make_env()
    assert isinstance(env.state.farms[0], Farm)


# ---------------------------------------------------------------------------
# Plant tiles dispatch to refresh_plant.
# ---------------------------------------------------------------------------

def test_refresh_tiles_dispatches_plant_tiles_to_refresh_plant():
    """Two unwatered plants → both become weeds after refresh_tiles."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=False)
    farm.tiles[4][4] = _plant(consecutive_unwatered=1, watered_today=False)

    farm.refresh_tiles(env.state)

    assert isinstance(farm.tiles[5][5], WeedState)
    assert isinstance(farm.tiles[4][4], WeedState)


def test_refresh_tiles_keeps_watered_plant():
    """A watered plant survives the refresh (counter resets, no weed)."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=True)

    farm.refresh_tiles(env.state)

    assert isinstance(farm.tiles[5][5], PlantState)
    assert farm.tiles[5][5].consecutive_unwatered == 0
    assert farm.tiles[5][5].watered_today is False


def test_refresh_tiles_resets_watered_today_for_surviving_plant():
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _plant(consecutive_unwatered=0, watered_today=True)

    farm.refresh_tiles(env.state)

    assert isinstance(farm.tiles[5][5], PlantState)
    assert farm.tiles[5][5].watered_today is False


# ---------------------------------------------------------------------------
# Animal tiles dispatch to refresh_animal.
# ---------------------------------------------------------------------------

def test_refresh_tiles_dispatches_animal_tiles_to_refresh_animal():
    """A fed animal with consecutive_unfed=1 escapes after refresh_tiles."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _structure(animal="GOOSE", fed_today=False,
                                  consecutive_unfed=1)

    farm.refresh_tiles(env.state)

    assert farm.tiles[5][5].animal is None


def test_refresh_tiles_keeps_fed_animal():
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _structure(animal="GOOSE", fed_today=True,
                                  consecutive_unfed=0)

    farm.refresh_tiles(env.state)

    assert farm.tiles[5][5].animal == "GOOSE"
    assert farm.tiles[5][5].fed_today is False
    assert farm.tiles[5][5].fertilizer_available == 1


def test_refresh_tiles_empty_structure_resets_daily_flags():
    """A structure with no animal just resets fed/cared flags."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _structure(animal=None, fed_today=True)

    # Set non-default flags to verify they reset.
    farm.tiles[5][5].cared_today = True

    farm.refresh_tiles(env.state)

    assert farm.tiles[5][5].animal is None
    assert farm.tiles[5][5].fed_today is False
    assert farm.tiles[5][5].cared_today is False


# ---------------------------------------------------------------------------
# None / WeedState / LOCKED tiles are untouched.
# ---------------------------------------------------------------------------

def test_refresh_tiles_leaves_empty_tiles_empty():
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)

    farm.refresh_tiles(env.state)

    for r in range(10):
        for c in range(10):
            assert farm.tiles[r][c] is None


def test_refresh_tiles_leaves_existing_weeds_untouched():
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[5][5] = WeedState()
    farm.tiles[3][3] = WeedState()

    farm.refresh_tiles(env.state)

    assert isinstance(farm.tiles[5][5], WeedState)
    assert isinstance(farm.tiles[3][3], WeedState)


def test_refresh_tiles_leaves_locked_tiles_untouched():
    """LOCKED string tiles (in unbought quadrants) are not refreshed."""
    env = _make_env(farmer=(4, 4), players=2)
    farm = _farm(env)
    # Mark a few tiles as LOCKED (e.g. unbought quadrant).
    farm.tiles[0][5] = "LOCKED"
    farm.tiles[5][0] = "LOCKED"

    farm.refresh_tiles(env.state)

    assert farm.tiles[0][5] == "LOCKED"
    assert farm.tiles[5][0] == "LOCKED"


# ---------------------------------------------------------------------------
# Mixed grids dispatch each tile appropriately.
# ---------------------------------------------------------------------------

def test_refresh_tiles_mixed_grid_dispatches_each_appropriately():
    """Plant + animal + weed + empty + LOCKED in the same grid all handled."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    farm.tiles[0][0] = _plant(consecutive_unwatered=1, watered_today=False)  # → weed
    farm.tiles[0][1] = _structure(animal="GOOSE", fed_today=False,
                                  consecutive_unfed=1)                       # → escapes
    farm.tiles[0][2] = WeedState()                                          # stays
    # [0][3] stays None
    farm.tiles[0][4] = "LOCKED"                                             # stays

    farm.refresh_tiles(env.state)

    assert isinstance(farm.tiles[0][0], WeedState)         # plant → weed
    assert farm.tiles[0][1].animal is None                 # animal escaped
    assert isinstance(farm.tiles[0][2], WeedState)         # weed stays
    assert farm.tiles[0][3] is None                        # empty stays
    assert farm.tiles[0][4] == "LOCKED"                    # locked stays


# ---------------------------------------------------------------------------
# Edge cases — empty grid, full grid, multi-player.
# ---------------------------------------------------------------------------

def test_refresh_tiles_empty_grid_is_noop():
    """A farm with zero tiles should not raise."""
    env = _make_env(rows=0, cols=0, farmer=(0, 0), players=2)
    farm = _farm(env)
    # Should not raise on an empty grid.
    farm.refresh_tiles(env.state)


def test_refresh_tiles_full_grid_of_plants_dispatches_all():
    """Every tile a plant → every tile refreshed (here, all become weeds)."""
    env = _make_env(farmer=(5, 5), players=2)
    farm = _farm(env)
    for r in range(10):
        for c in range(10):
            farm.tiles[r][c] = _plant(consecutive_unwatered=1, watered_today=False)

    farm.refresh_tiles(env.state)

    for r in range(10):
        for c in range(10):
            assert isinstance(farm.tiles[r][c], WeedState)


def test_refresh_tiles_only_touches_target_farm():
    """Calling refresh_tiles on farm 0 leaves farm 1 untouched."""
    env = _make_env(farmer=(5, 5), players=2)
    farm0 = _farm(env, 0)
    farm1 = _farm(env, 1)
    farm0.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=False)
    farm1.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=False)

    farm0.refresh_tiles(env.state)

    assert isinstance(farm0.tiles[5][5], WeedState)
    # farm1 still has its plant — refresh_tiles on farm0 didn't touch it.
    assert isinstance(farm1.tiles[5][5], PlantState)
    assert farm1.tiles[5][5].consecutive_unwatered == 1


# ---------------------------------------------------------------------------
# Uses state.step / state.day for plant decay (delegates to refresh_plant).
# ---------------------------------------------------------------------------

def test_refresh_tiles_passes_state_to_refresh_plant_for_decay():
    """refresh_plant uses state.step for the decay calculation; refresh_tiles
    forwards the state so decay advances correctly past max_lifespan_step."""
    env = _make_env(farmer=(5, 5), step=20, day=1, players=2)
    farm = _farm(env)
    # Plant past lifespan, with yield_units=2 and unwatered so decay is observable
    # only if the plant survives the weed check — water it to keep it alive.
    farm.tiles[5][5] = _plant(consecutive_unwatered=0, watered_today=True,
                              max_lifespan_step=10, yield_units=2)

    farm.refresh_tiles(env.state)

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    # (20 - 10) % 2 == 0 → not a decay turn; yield_units unchanged.
    assert tile.yield_units == 2


def test_refresh_tiles_decay_turn_reduces_yield_via_refresh_plant():
    env = _make_env(farmer=(5, 5), step=21, day=1, players=2)
    farm = _farm(env)
    farm.tiles[5][5] = _plant(consecutive_unwatered=0, watered_today=True,
                              max_lifespan_step=10, yield_units=2)

    farm.refresh_tiles(env.state)

    tile = farm.tiles[5][5]
    assert isinstance(tile, PlantState)
    # (21 - 10) % 2 == 1 → decay turn; yield_units drops by 1.
    assert tile.yield_units == 1