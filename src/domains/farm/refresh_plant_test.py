"""Tests for end-of-day plant refresh: miss counters, weed conversion, decay."""
import pytest

from tests.fixtures import _make_env
from src.domains.farm.refresh_plant import refresh_plant
from src.models.farm import PlantState, WeedState


def _plant(planted_day=0, max_lifespan_step=100, watered_today=False,
           consecutive_unwatered=0, yield_units=0, fertilized_until_day=0,
           crop="WHEAT"):
    return PlantState(
        crop=crop, planted_day=planted_day,
        max_lifespan_step=max_lifespan_step,
        watered_today=watered_today,
        consecutive_unwatered=consecutive_unwatered,
        yield_units=yield_units,
        fertilized_until_day=fertilized_until_day,
    )


class TestRefreshPlant:
    """Tests for `refresh_plant`."""

    # ---------------------------------------------------------------------------
    # Miss counter + watered_today reset.
    # ---------------------------------------------------------------------------

    def test_unwatered_increments_consecutive_unwatered(self):
        env = _make_env(farmer=(5, 5), step=24)  # day 1 rollover
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(consecutive_unwatered=0, watered_today=False)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        tile = farm.tiles[5][5]
        assert isinstance(tile, PlantState)
        assert tile.consecutive_unwatered == 1
        assert tile.watered_today is False

    def test_watered_resets_consecutive_unwatered(self):
        env = _make_env(farmer=(5, 5), step=24)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=True)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        tile = farm.tiles[5][5]
        assert isinstance(tile, PlantState)
        assert tile.consecutive_unwatered == 0
        assert tile.watered_today is False  # reset for the new day

    def test_first_miss_when_planted_and_not_watered(self):
        """A fresh plant (counter=0) not watered today → counter becomes 1."""
        env = _make_env(farmer=(5, 5), step=24)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(consecutive_unwatered=0, watered_today=False)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert farm.tiles[5][5].consecutive_unwatered == 1

    # ---------------------------------------------------------------------------
    # Weed conversion — two consecutive misses.
    # ---------------------------------------------------------------------------

    def test_consecutive_unwatered_two_becomes_weed(self):
        env = _make_env(farmer=(5, 5), step=24)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=False)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert isinstance(farm.tiles[5][5], WeedState)

    def test_watered_plant_survives_when_counter_was_one(self):
        env = _make_env(farmer=(5, 5), step=24)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(consecutive_unwatered=1, watered_today=True)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert isinstance(farm.tiles[5][5], PlantState)

    # ---------------------------------------------------------------------------
    # Decay — past max_lifespan_step, yield_units drops every other turn.
    # ---------------------------------------------------------------------------

    def test_decay_drops_yield_every_other_turn_past_lifespan(self):
        env = _make_env(farmer=(5, 5), step=101)  # 1 past lifespan=100
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=0,
                                  watered_today=True, yield_units=5)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        # (101 - 100) % 2 == 1 → decay tick fires.
        assert farm.tiles[5][5].yield_units == 4

    def test_decay_skips_on_even_offset_past_lifespan(self):
        env = _make_env(farmer=(5, 5), step=102)  # 2 past lifespan=100, even
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=0,
                                  watered_today=True, yield_units=5)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        # (102 - 100) % 2 == 0 → no decay tick this turn.
        assert farm.tiles[5][5].yield_units == 5

    def test_decays_to_zero_becomes_weed(self):
        env = _make_env(farmer=(5, 5), step=101)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=0,
                                  watered_today=True, yield_units=1)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert isinstance(farm.tiles[5][5], WeedState)

    def test_decay_floor_at_zero_does_not_go_negative(self):
        env = _make_env(farmer=(5, 5), step=101)
        farm = env.state.farms[0]
        # yield_units=0 but not yet converted (decay tick happens before weed check
        # would trigger from the decay path — here we start at 0 with no prior weed).
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=0,
                                  watered_today=True, yield_units=0)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        # yield was already 0; decay path converts to weed.
        assert isinstance(farm.tiles[5][5], WeedState)

    # ---------------------------------------------------------------------------
    # Decay only applies past max_lifespan_step.
    # ---------------------------------------------------------------------------

    def test_no_decay_before_lifespan(self):
        env = _make_env(farmer=(5, 5), step=99)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=0,
                                  watered_today=True, yield_units=5)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert farm.tiles[5][5].yield_units == 5  # unchanged

    # ---------------------------------------------------------------------------
    # Neglect takes precedence — weed conversion happens before decay is evaluated.
    # ---------------------------------------------------------------------------

    def test_neglect_converts_to_weed_even_past_lifespan(self):
        env = _make_env(farmer=(5, 5), step=101)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(max_lifespan_step=100, consecutive_unwatered=1,
                                  watered_today=False, yield_units=5)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        assert isinstance(farm.tiles[5][5], WeedState)

    # ---------------------------------------------------------------------------
    # Parametric sanity across crops.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
    def test_works_for_every_crop(self, crop):
        env = _make_env(farmer=(5, 5), step=24)
        farm = env.state.farms[0]
        farm.tiles[5][5] = _plant(crop=crop, consecutive_unwatered=0, watered_today=True)

        refresh_plant(env.state, farm, 5, 5, farm.tiles[5][5])

        tile = farm.tiles[5][5]
        assert isinstance(tile, PlantState)
        assert tile.consecutive_unwatered == 0
        assert tile.watered_today is False