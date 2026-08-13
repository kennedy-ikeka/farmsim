"""Tests for the Farm controller — dispatch of each farm action type."""
import types

import pytest

from tests.fixtures import _make_env
from src.domains.farm import Farm
from src.models.action import (
    BuildCoopActionState,
    BuildPastureActionState,
    CareActionState,
    CollectFertilizerActionState,
    DigActionState,
    FeedActionState,
    FertilizeActionState,
    HarvestActionState,
    MoveActionState,
    PassActionState,
    PickupActionState,
    PlaceActionState,
    PlantActionState,
    WaterActionState,
)
from src.models.farm import PlantState, WeedState, AnimalState


class TestFarmController:
    """Tests for the Farm controller structure."""

    # ---------------------------------------------------------------------------
    # The fixture-built farm is already a Farm controller (IS-A FarmState).
    # ---------------------------------------------------------------------------

    def test_farm_in_state_is_farm_controller(self):
        env = _make_env()
        assert isinstance(env.state.farms[0], Farm)


class TestFarmApply:
    """Tests for `Farm.apply`."""

    # ---------------------------------------------------------------------------
    # PASS is a no-op.
    # ---------------------------------------------------------------------------

    def test_pass_is_noop(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.apply(env.state, [5, 5], PassActionState(type="PASS"), 0)
        assert farm.farmer == [5, 5]  # nothing changed

    # ---------------------------------------------------------------------------
    # Move actions dispatch to move_unit.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("direction, start, expected", [
        ("NORTH", [5, 5], [4, 5]),
        ("SOUTH", [5, 5], [6, 5]),
        ("EAST", [5, 5], [5, 6]),
        ("WEST", [5, 5], [5, 4]),
    ])
    def test_move_dispatches(self, direction, start, expected):
        env = _make_env(farmer=tuple(start))
        farm = env.state.farms[0]
        # move_unit mutates the position list in place; the controller passes
        # farm.farmer, so we do the same to observe the effect on farm.farmer.
        farm.apply(env.state, farm.farmer, MoveActionState(type=direction), 0)
        assert farm.farmer == expected

    # ---------------------------------------------------------------------------
    # PLANT dispatches to plant.
    # ---------------------------------------------------------------------------

    def test_plant_dispatches(self):
        env = _make_env(farmer=(4, 4), seeds={"WHEAT": 3})
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], PlantActionState(type="PLANT", crop="WHEAT"), 0)
        assert isinstance(farm.tiles[4][4], PlantState)
        assert farm.tiles[4][4].crop == "WHEAT"
        assert env.state.privates[0].seeds.WHEAT == 2

    # ---------------------------------------------------------------------------
    # WATER dispatches to water.
    # ---------------------------------------------------------------------------

    def test_water_dispatches(self):
        env = _make_env(farmer=(4, 4), seeds={"WHEAT": 1})
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], PlantActionState(type="PLANT", crop="WHEAT"), 0)
        assert farm.tiles[4][4].watered_today is False
        farm.apply(env.state, [4, 4], WaterActionState(type="WATER"), 0)
        assert farm.tiles[4][4].watered_today is True

    # ---------------------------------------------------------------------------
    # HARVEST dispatches to harvest.
    # ---------------------------------------------------------------------------

    def test_harvest_dispatches(self):
        env = _make_env(farmer=(4, 4), seeds={"WHEAT": 1}, day=10)
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], PlantActionState(type="PLANT", crop="WHEAT"), 0)
        farm.tiles[4][4].yield_units = 5
        # WHEAT first_yield_day is 2; advance the day so harvest can fire.
        env.state.day = 13
        farm.apply(env.state, [4, 4], HarvestActionState(type="HARVEST"), 0)
        assert farm.tiles[4][4] is None  # one-time crop consumed
        assert env.state.privates[0].shed.WHEAT == 5

    # ---------------------------------------------------------------------------
    # FERTILIZE dispatches to fertilize.
    # ---------------------------------------------------------------------------

    def test_fertilize_dispatches(self):
        env = _make_env(farmer=(4, 4), seeds={"WHEAT": 1}, day=2)
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], PlantActionState(type="PLANT", crop="WHEAT"), 0)
        env.state.privates[0].shed.FERTILIZER = 1
        farm.apply(env.state, [4, 4], FertilizeActionState(type="FERTILIZE"), 0)
        assert farm.tiles[4][4].fertilized_until_day == 2 + 3
        assert env.state.privates[0].shed.FERTILIZER == 0

    # ---------------------------------------------------------------------------
    # DIG dispatches to dig.
    # ---------------------------------------------------------------------------

    def test_dig_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = WeedState()
        farm.apply(env.state, [4, 4], DigActionState(type="DIG"), 0)
        assert farm.tiles[4][4] is None

    # ---------------------------------------------------------------------------
    # BUILD_COOP / BUILD_PASTURE dispatch to build_structure.
    # ---------------------------------------------------------------------------

    def test_build_coop_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], BuildCoopActionState(type="BUILD_COOP"), 0)
        assert isinstance(farm.tiles[4][4], AnimalState)
        assert farm.tiles[4][4].kind == "COOP"

    def test_build_pasture_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.apply(env.state, [4, 4], BuildPastureActionState(type="BUILD_PASTURE"), 0)
        assert isinstance(farm.tiles[4][4], AnimalState)
        assert farm.tiles[4][4].kind == "PASTURE"

    # ---------------------------------------------------------------------------
    # FEED dispatches to feed.
    # ---------------------------------------------------------------------------

    def test_feed_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = AnimalState(kind="COOP", animal="GOOSE")
        env.state.privates[0].shed.WHEAT = 1
        farm.apply(env.state, [4, 4], FeedActionState(type="FEED"), 0)
        assert farm.tiles[4][4].fed_today is True
        assert env.state.privates[0].shed.WHEAT == 0

    # ---------------------------------------------------------------------------
    # COLLECT_FERTILIZER dispatches to collect_fertilizer.
    # ---------------------------------------------------------------------------

    def test_collect_fertilizer_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=1)
        farm.apply(env.state, [4, 4], CollectFertilizerActionState(type="COLLECT_FERTILIZER"), 0)
        assert farm.tiles[4][4].fertilizer_available == 0
        assert env.state.privates[0].shed.FERTILIZER == 1

    # ---------------------------------------------------------------------------
    # CARE dispatches to care.
    # ---------------------------------------------------------------------------

    def test_care_dispatches(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = AnimalState(kind="COOP", animal="GOOSE")
        farm.apply(env.state, [4, 4], CareActionState(type="CARE"), 0)
        assert farm.tiles[4][4].cared_today is True

    # ---------------------------------------------------------------------------
    # PICKUP dispatches to pickup (needs shed-adjacent tile).
    # ---------------------------------------------------------------------------

    def test_pickup_dispatches(self):
        # (4,4) is a shed-adjacent center tile for a 10x10 board (half=5).
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 2
        farm.apply(env.state, [4, 4], PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)
        assert env.state.privates[0].shed.WHEAT == 1
        assert env.state.privates[0].inventories[0]["WHEAT"] == 1

    # ---------------------------------------------------------------------------
    # PLACE dispatches to place.
    # ---------------------------------------------------------------------------

    def test_place_dispatches(self):
        # Drop an item back into the shed from the farmer's inventory.
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].inventories = [{"WHEAT": 1}]
        env.state.privates[0].shed.WHEAT = 0
        farm.apply(env.state, [4, 4], PlaceActionState(type="PLACE", item="WHEAT", count=1), 0)
        assert env.state.privates[0].shed.WHEAT == 1
        assert env.state.privates[0].inventories[0]["WHEAT"] == 0

    # ---------------------------------------------------------------------------
    # Unsupported action raises ValueError.
    # ---------------------------------------------------------------------------

    def test_unsupported_action_raises(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        bogus = types.SimpleNamespace(type="BOGUS")
        with pytest.raises(ValueError, match="Unsupported farm action"):
            farm.apply(env.state, [4, 4], bogus, 0)