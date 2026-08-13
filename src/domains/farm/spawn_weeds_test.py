"""Tests for end-of-day weed spawn on empty unlocked tiles."""
import random

from tests.fixtures import _make_env
from src.domains.farm.spawn_weeds import spawn_weeds
from src.models.farm import PlantState, WeedState


class TestSpawnWeeds:
    """Tests for `spawn_weeds`."""

    # ---------------------------------------------------------------------------
    # Chance = 1.0 — every empty tile spawns a weed.
    # ---------------------------------------------------------------------------

    def test_chance_one_spawns_on_every_empty_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        rng = random.Random(0)
        spawn_weeds(farm, weed_spawn_chance=1.0, rng=rng)
        for r in range(len(farm.tiles)):
            for c in range(len(farm.tiles[r])):
                assert isinstance(farm.tiles[r][c], WeedState)

    # ---------------------------------------------------------------------------
    # Chance = 0.0 — no weeds spawn.
    # ---------------------------------------------------------------------------

    def test_chance_zero_spawns_nothing(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        rng = random.Random(0)
        spawn_weeds(farm, weed_spawn_chance=0.0, rng=rng)
        for r in range(len(farm.tiles)):
            for c in range(len(farm.tiles[r])):
                assert farm.tiles[r][c] is None

    # ---------------------------------------------------------------------------
    # Occupied tiles are never replaced.
    # ---------------------------------------------------------------------------

    def test_does_not_replace_plants(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        rng = random.Random(0)
        spawn_weeds(farm, weed_spawn_chance=1.0, rng=rng)
        assert isinstance(farm.tiles[5][5], PlantState)  # not overwritten

    def test_does_not_replace_existing_weeds(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = WeedState()
        rng = random.Random(0)
        spawn_weeds(farm, weed_spawn_chance=1.0, rng=rng)
        assert isinstance(farm.tiles[5][5], WeedState)

    # ---------------------------------------------------------------------------
    # Determinism — same seed produces same weed layout.
    # ---------------------------------------------------------------------------

    def test_deterministic_with_same_rng_seed(self):
        env1 = _make_env(farmer=(5, 5))
        env2 = _make_env(farmer=(5, 5))
        spawn_weeds(env1.state.farms[0], weed_spawn_chance=0.5, rng=random.Random(42))
        spawn_weeds(env2.state.farms[0], weed_spawn_chance=0.5, rng=random.Random(42))
        for r in range(10):
            for c in range(10):
                t1 = env1.state.farms[0].tiles[r][c]
                t2 = env2.state.farms[0].tiles[r][c]
                assert (t1 is None) == (t2 is None)
                if t1 is not None:
                    assert isinstance(t1, WeedState) and isinstance(t2, WeedState)

    def test_different_seeds_produce_different_layouts(self):
        """Sanity: two different RNG seeds usually produce different layouts."""
        env1 = _make_env(farmer=(5, 5))
        env2 = _make_env(farmer=(5, 5))
        spawn_weeds(env1.state.farms[0], weed_spawn_chance=0.5, rng=random.Random(1))
        spawn_weeds(env2.state.farms[0], weed_spawn_chance=0.5, rng=random.Random(999))
        tiles1 = [env1.state.farms[0].tiles[r][c] for r in range(10) for c in range(10)]
        tiles2 = [env2.state.farms[0].tiles[r][c] for r in range(10) for c in range(10)]
        assert tiles1 != tiles2

    # ---------------------------------------------------------------------------
    # Non-square grids — bounds derived from tile grid, not hardcoded.
    # ---------------------------------------------------------------------------

    def test_works_on_non_square_grid(self):
        env = _make_env(rows=3, cols=4, farmer=(1, 1))
        farm = env.state.farms[0]
        spawn_weeds(farm, weed_spawn_chance=1.0, rng=random.Random(0))
        for r in range(3):
            for c in range(4):
                assert isinstance(farm.tiles[r][c], WeedState)

    # ---------------------------------------------------------------------------
    # Small grid edge case.
    # ---------------------------------------------------------------------------

    def test_small_grid_all_empty(self):
        env = _make_env(rows=2, cols=2, farmer=(0, 0))
        farm = env.state.farms[0]
        spawn_weeds(farm, weed_spawn_chance=1.0, rng=random.Random(0))
        for r in range(2):
            for c in range(2):
                assert isinstance(farm.tiles[r][c], WeedState)