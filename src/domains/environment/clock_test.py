"""Tests for the Clock controller — time advancement and end-of-day refresh."""
import random

from tests.fixtures import _make_env
from src.domains.environment.clock import Clock
from src.models.farm import AnimalState, PlantState, WeedState
from src.utils.config import (
    EPISODE_STEPS,
    SHED_CAPACITY,
    TURNS_PER_DAY,
    WEED_SPAWN_CHANCE,
)


def _rng(seed=0):
    return random.Random(seed)


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


class TestClock:
    """Tests for `Clock` defaults and custom config."""

    def test_defaults_match_config(self):
        clock = Clock()
        assert clock.turns_per_day == TURNS_PER_DAY
        assert clock.episode_steps == EPISODE_STEPS
        assert clock.shed_capacity == SHED_CAPACITY
        assert clock.weed_spawn_chance == WEED_SPAWN_CHANCE

    def test_accepts_custom_config(self):
        clock = Clock(turns_per_day=4, episode_steps=10, shed_capacity=50,
                      weed_spawn_chance=0.0)
        assert clock.turns_per_day == 4
        assert clock.episode_steps == 10
        assert clock.shed_capacity == 50
        assert clock.weed_spawn_chance == 0.0


class TestAdvanceTime:
    """Tests for `Clock.advance_time` — step/hour/day advancement and done flag."""

    def test_increments_step(self):
        env = _make_env(step=0)
        clock = env.clock
        clock.advance_time(env.state, _rng())
        assert env.state.step == 1

    def test_sets_hour_from_step_mod_turns_per_day(self):
        env = _make_env(step=0)
        clock = env.clock  # default turns_per_day=24
        clock.advance_time(env.state, _rng())
        assert env.state.hour == 1 % 24

    def test_rolls_hour_back_to_zero_at_turns_per_day(self):
        env = _make_env(step=23)  # next step is 24 → hour 0 of day 1
        clock = env.clock
        clock.advance_time(env.state, _rng())
        assert env.state.step == 24
        assert env.state.hour == 0
        assert env.state.day == 1

    def test_sets_day_from_step_div_turns_per_day(self):
        env = _make_env(step=47)  # next step is 48 → day 2
        clock = env.clock
        clock.advance_time(env.state, _rng())
        assert env.state.step == 48
        assert env.state.day == 2

    def test_returns_false_before_episode_end(self):
        env = _make_env(step=0)
        done = env.clock.advance_time(env.state, _rng())
        assert done is False

    def test_returns_true_at_episode_steps(self):
        env = _make_env(step=EPISODE_STEPS - 1)
        done = env.clock.advance_time(env.state, _rng())
        assert done is True
        assert env.state.step == EPISODE_STEPS

    def test_returns_true_past_episode_steps(self):
        env = _make_env(step=EPISODE_STEPS)
        done = env.clock.advance_time(env.state, _rng())
        assert done is True

    def test_respects_custom_episode_steps(self):
        env = _make_env(step=9)
        # Replace the env's clock with a custom one.
        env.clock = Clock(episode_steps=10)
        done = env.clock.advance_time(env.state, _rng())
        assert done is True
        assert env.state.step == 10

    def test_no_refresh_when_day_does_not_roll_over(self):
        """step 0 → 1 (same day): hires_today stays, hands stay."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], step=0)
        env.state.farms[0].hires_today = 3
        env.clock.advance_time(env.state, _rng())
        assert env.state.farms[0].hires_today == 3  # unchanged
        assert env.state.farms[0].hands == [[5, 4]]  # unchanged

    def test_runs_refresh_when_day_rolls_over(self):
        """step 23 → 24 (day 0 → 1): hires reset, hands cleared."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], step=TURNS_PER_DAY - 1)
        env.state.farms[0].hires_today = 3
        env.clock.advance_time(env.state, _rng())
        assert env.state.farms[0].hires_today == 0
        assert env.state.farms[0].hands == []

    def test_respects_custom_turns_per_day_for_rollover(self):
        """With turns_per_day=4, rollover happens at step 4 (not 24)."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], step=3)
        env.clock = Clock(turns_per_day=4)
        env.state.farms[0].hires_today = 2
        env.clock.advance_time(env.state, _rng())
        assert env.state.step == 4
        assert env.state.day == 1
        assert env.state.farms[0].hires_today == 0  # refresh ran
        assert env.state.farms[0].hands == []

    def test_custom_turns_per_day_no_rollover_before_threshold(self):
        """With turns_per_day=4, step 2 → 3 is still day 0 — no refresh."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], step=2)
        env.clock = Clock(turns_per_day=4)
        env.state.farms[0].hires_today = 2
        env.clock.advance_time(env.state, _rng())
        assert env.state.day == 0
        assert env.state.farms[0].hires_today == 2  # unchanged
        assert env.state.farms[0].hands == [[5, 4]]

    def test_repeated_calls_advance_correctly(self):
        env = _make_env(step=0)
        clock = env.clock
        for _ in range(5):
            clock.advance_time(env.state, _rng())
        assert env.state.step == 5
        assert env.state.day == 0

    def test_multiple_day_rollovers(self):
        """Advancing 48 steps from step 0 → day 2, two refreshes ran."""
        env = _make_env(farmer=(5, 5), step=0)
        clock = env.clock
        for _ in range(TURNS_PER_DAY * 2):
            clock.advance_time(env.state, _rng())
        assert env.state.step == TURNS_PER_DAY * 2
        assert env.state.day == 2


class TestEndOfDayRefresh:
    """Tests for `Clock.end_of_day_refresh` — direct invocation."""

    def test_runs_for_every_player(self):
        """Both players' farms get hires reset and hands cleared."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], players=2)
        for p in range(2):
            env.state.farms[p].hires_today = 3
            env.state.farms[p].hands = [[5, 4]]
        env.clock.end_of_day_refresh(env.state, _rng())
        for p in range(2):
            assert env.state.farms[p].hires_today == 0
            assert env.state.farms[p].hands == []

    def test_single_player(self):
        """With one player, only that player's farm is refreshed."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], players=1)
        env.state.farms[0].hires_today = 5
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.farms[0].hires_today == 0
        assert env.state.farms[0].hands == []

    def test_converts_neglected_plant_to_weed(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.state.farms[0].tiles[5][5] = _plant(consecutive_unwatered=1,
                                                watered_today=False)
        env.clock.end_of_day_refresh(env.state, _rng())
        assert isinstance(env.state.farms[0].tiles[5][5], WeedState)

    def test_keeps_watered_plant(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.state.farms[0].tiles[5][5] = _plant(consecutive_unwatered=1,
                                                watered_today=True)
        env.clock.end_of_day_refresh(env.state, _rng())
        tile = env.state.farms[0].tiles[5][5]
        assert isinstance(tile, PlantState)
        assert tile.consecutive_unwatered == 0

    def test_escapes_neglected_animal(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.state.farms[0].tiles[5][5] = _structure(animal="GOOSE", fed_today=False,
                                                    consecutive_unfed=1)
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.farms[0].tiles[5][5].animal is None

    def test_refreshes_both_players_tiles(self):
        env = _make_env(farmer=(5, 5), players=2)
        for p in range(2):
            env.state.farms[p].tiles[5][5] = _plant(consecutive_unwatered=1,
                                                    watered_today=False)
        env.clock.end_of_day_refresh(env.state, _rng())
        for p in range(2):
            assert isinstance(env.state.farms[p].tiles[5][5], WeedState)

    def test_chance_zero_spawns_no_weeds(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.clock = Clock(weed_spawn_chance=0.0)
        env.clock.end_of_day_refresh(env.state, _rng())
        for p in range(2):
            for r in range(10):
                for c in range(10):
                    assert env.state.farms[p].tiles[r][c] is None

    def test_chance_one_spawns_weeds_on_empty_tiles(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.clock = Clock(weed_spawn_chance=1.0)
        env.clock.end_of_day_refresh(env.state, _rng())
        for p in range(2):
            for r in range(10):
                for c in range(10):
                    assert isinstance(env.state.farms[p].tiles[r][c], WeedState)

    def test_does_not_spawn_on_occupied_tiles(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.state.farms[0].tiles[5][5] = _plant(watered_today=True)
        env.clock = Clock(weed_spawn_chance=1.0)
        env.clock.end_of_day_refresh(env.state, _rng())
        # Plant survived (watered) and wasn't replaced by a spawned weed.
        assert isinstance(env.state.farms[0].tiles[5][5], PlantState)

    def test_drops_hand_inventory_to_shed(self):
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], players=2)
        env.state.farms[0].hires_today = 1
        env.state.privates[0].inventories = [{}, {"WHEAT": 2}]
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.privates[0].shed.WHEAT == 2
        # Hand gone; inventories truncated to len 1 (farmer only).
        assert env.state.farms[0].hands == []
        assert len(env.state.privates[0].inventories) == 1

    def test_shed_capacity_caps_drop(self):
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], players=2)
        env.clock = Clock(shed_capacity=5)
        env.state.farms[0].hires_today = 1
        # Pre-fill shed with 4 carrots; hand has 3 wheat → only 1 fits.
        env.state.privates[0].shed.CARROT = 4
        env.state.privates[0].inventories = [{}, {"WHEAT": 3}]
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.privates[0].shed.WHEAT == 1  # 5 capacity - 4 carrot = 1 space

    def test_farmer_keeps_inventory(self):
        env = _make_env(farmer=(5, 5), players=2)
        env.state.privates[0].inventories = [{"WHEAT": 3}]
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.privates[0].inventories[0] == {"WHEAT": 3}

    def test_truncates_inventories_to_farmer_only(self):
        env = _make_env(farmer=(5, 5), hands=[[5, 4], [5, 3]], players=2)
        env.state.farms[0].hires_today = 2
        env.state.privates[0].inventories = [{}, {"WHEAT": 2}, {"EGG": 1}]
        env.clock.end_of_day_refresh(env.state, _rng())
        assert len(env.state.privates[0].inventories) == 1
        assert env.state.privates[0].shed.WHEAT == 2
        assert env.state.privates[0].shed.EGG == 1

    def test_callable_directly(self):
        """end_of_day_refresh doesn't depend on advance_time state changes."""
        env = _make_env(farmer=(5, 5), hands=[[5, 4]], players=2)
        env.state.farms[0].hires_today = 7
        # Call directly — no step/day change required.
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.farms[0].hires_today == 0
        assert env.state.farms[0].hands == []

    def test_does_not_advance_step(self):
        """end_of_day_refresh mutates farms/privates but leaves step/hour/day alone."""
        env = _make_env(farmer=(5, 5), step=5, day=0, players=2)
        env.clock.end_of_day_refresh(env.state, _rng())
        assert env.state.step == 5
        assert env.state.day == 0
        assert env.state.hour == 5 % 24