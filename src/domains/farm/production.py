"""Pure production-chain math shared across farm action modules.

These helpers compute the achievable yield / production over the remaining
episode under an optimal-completion assumption (the player waters / feeds /
cares on every required day and harvests + sells in time). They are used by
the `future_gain` / `future_usage` functions on PLANT, WATER, FERTILIZE,
BUILD_COOP / BUILD_PASTURE, PLACE, FEED, CARE, and by the market-side
BUY_SEED / BUY_ANIMAL future-gain functions.
"""
import math

from src.utils.config import EPISODE_STEPS, TURNS_PER_DAY
from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG

EPISODE_DAYS = EPISODE_STEPS // TURNS_PER_DAY  # 30


def crop_future_yield(crop: str, planted_day: int, fertilized: bool = False) -> int:
    """Achievable yield units for a one-time crop planted at `planted_day`,
    counting watering-window days that fit before the episode ends. 0 for
    ongoing crops (not modeled)."""
    cfg = CROP_CONFIG[crop]
    if cfg.yield_type != "one-time":
        return 0
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    per_day = 2 if fertilized else 1
    return sum(
        per_day
        for d in range(window_start, window_end + 1)
        if planted_day + d < EPISODE_DAYS
    )


def crop_window_days_remaining(crop: str, planted_day: int, from_day: int) -> int:
    """Number of watering-window days strictly after `from_day` that still fit
    before the episode ends. Used by FERTILIZE (today is the fertilize, future
    days are the waters) and PLANT future_usage (waters the player must do)."""
    cfg = CROP_CONFIG[crop]
    if cfg.yield_type != "one-time":
        return 0
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    return sum(
        1
        for d in range(window_start, window_end + 1)
        if from_day < planted_day + d < EPISODE_DAYS
    )


def animal_future_production(animal: str, placed_day: int) -> tuple[int, int]:
    """(yield_units, fertilizer_days) over the remaining episode, assuming the
    animal is fed+cared daily and harvested each production day (so `max_held`
    never binds)."""
    cfg = ANIMAL_CONFIG[animal]
    yield_units = 0
    prev = placed_day
    d = placed_day + cfg.first_yield_day
    while d < EPISODE_DAYS:
        bank = d - prev  # fed+cared days since the last production
        yield_units += min(1 + bank, cfg.max_held)
        prev = d
        d += cfg.interval
    fertilizer_days = max(0, EPISODE_DAYS - placed_day)
    return yield_units, fertilizer_days