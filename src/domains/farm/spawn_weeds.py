"""End-of-day weed spawn — stochastic weeds on empty unlocked tiles.

Each empty unlocked tile (`tile is None`) has a `weed_spawn_chance` probability
of spawning a `WeedState` at day rollover. Locked tiles and occupied tiles are
left untouched.
"""
import random

from src.models.farm import FarmState, WeedState


def spawn_weeds(farm: FarmState, weed_spawn_chance: float,
                rng: random.Random) -> None:
    """Probabilistically spawn weeds on empty tiles of `farm`, in place.

    Uses the supplied `rng` for all rolls so callers control determinism.
    """
    for r in range(len(farm.tiles)):
        for c in range(len(farm.tiles[r])):
            if farm.tiles[r][c] is None and rng.random() < weed_spawn_chance:
                farm.tiles[r][c] = WeedState()