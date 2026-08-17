"""Production-chain helpers for action pipelines.

These feed the `get_<action>_pipeline` functions: they compute the
state-dependent counts of downstream actions (how many WATERs a crop still
needs, on which days an animal yields, how many days a placed animal stays
productive) so a pipeline can return concrete `ActionState` instances.

`animal_pipeline` is shared by BUILD_COOP / BUILD_PASTURE / PLACE / BUY_ANIMAL
— every path that ends with a placed animal has the same per-day care +
harvest + sell tail.
"""
import math

from src.utils.config import EPISODE_STEPS, TURNS_PER_DAY
from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG
from src.models.action import (
    ActionState,
    WaterActionState,
    HarvestActionState,
    SellActionState,
    FeedActionState,
    CareActionState,
    CollectFertilizerActionState,
)

# Episode length in days (turns / TURNS_PER_DAY).
EPISODE_DAYS = EPISODE_STEPS // TURNS_PER_DAY  # 30


def crop_water_days_remaining(crop: str, planted_day: int, from_day: int) -> int:
    """Count of future watering-bonus days in the crop's bonus window.

    Window days `d` (days since planting) run from `ceil(max_yield_day / 2)`
    through `max_yield_day`. A day counts if it is strictly after `from_day`
    and within the episode. Each such day is one WATER that adds +1 yield
    (or +2 if fertilized — the fertilize bonus is realized through the same
    WATER actions, so the count of WATERs is unchanged).
    """
    cfg = CROP_CONFIG[crop]
    window_start = math.ceil(cfg.max_yield_day / 2)
    window_end = cfg.max_yield_day
    return sum(
        1 for d in range(window_start, window_end + 1)
        if from_day < planted_day + d < EPISODE_DAYS
    )


def crop_expected_yield(crop: str, planted_day: int, from_day: int) -> int:
    """Achievable yield under optimal watering = min(waters_remaining, max_yield).

    Every window water adds one harvestable unit (two if fertilized, but the
    bonus is counted at FERTILIZE time); the plant's lifetime output is capped
    by `max_yield`.
    """
    return min(
        crop_water_days_remaining(crop, planted_day, from_day),
        CROP_CONFIG[crop].max_yield,
    )


def animal_yield_days(animal: str, placed_day: int, from_day: int) -> list[int]:
    """Absolute day numbers on which `animal` yields, strictly after `from_day`.

    Starts at `first_yield_day` after placement and repeats every `interval`
    days until the episode ends.
    """
    cfg = ANIMAL_CONFIG[animal]
    days: list[int] = []
    d = cfg.first_yield_day
    while placed_day + d < EPISODE_DAYS:
        if placed_day + d > from_day:
            days.append(placed_day + d)
        d += cfg.interval
    return days


def animal_pipeline(animal: str, from_day: int) -> list[ActionState]:
    """Flattened downstream action sequence for a placed animal.

    Assumes the animal is placed on day `from_day`. For each remaining day in
    the episode: FEED + CARE + COLLECT_FERTILIZER, with a HARVEST on each
    scheduled yield day. Ends with one SELL of the accumulated product and
    one SELL of the accumulated fertilizer (one per surviving day).
    """
    cfg = ANIMAL_CONFIG[animal]
    yield_days = set(animal_yield_days(animal, from_day, from_day))
    remaining_days = max(0, EPISODE_DAYS - from_day - 1)
    pipeline: list[ActionState] = []
    for day in range(from_day + 1, EPISODE_DAYS):
        pipeline.append(FeedActionState(type="FEED"))
        pipeline.append(CareActionState(type="CARE"))
        pipeline.append(CollectFertilizerActionState(type="COLLECT_FERTILIZER"))
        if day in yield_days:
            pipeline.append(HarvestActionState(type="HARVEST"))
    if yield_days:
        pipeline.append(SellActionState(type="SELL", item=cfg.product, count=len(yield_days)))
    if remaining_days > 0:
        pipeline.append(SellActionState(type="SELL", item="FERTILIZER", count=remaining_days))
    return pipeline


def best_pasture_animal(prices) -> str:
    """The pasture animal (COW vs SHEEP) with the higher gross production value
    over the remaining episode, valued at current market prices."""
    best, best_value = "COW", 0.0
    for animal in ("COW", "SHEEP"):
        cfg = ANIMAL_CONFIG[animal]
        y = len(animal_yield_days(animal, 0, 0))
        value = y * getattr(prices, cfg.product, 0)
        if value >= best_value:
            best, best_value = animal, value
    return best