"""End-of-day animal refresh — escape checks, care bonus banking, fertilizer.

Runs at day rollover for every animal-structure tile. Two consecutive missed
feeds cause the animal to escape (animal removed, structure stays empty). Fed-
and-cared animals bank a `pending_care_bonus` (capped by `max_held - yield`).
Surviving animals make 1 fertilizer available at end of day.
"""
from src.models.animals import ANIMAL_CONFIG
from src.models.farm import AnimalState


def refresh_animal(tile: AnimalState) -> None:
    """Advance an animal-structure tile's end-of-day state in place.

    Mutates `tile` directly (never reassigns the slot — the structure stays):
      - empty structures: reset `fed_today`/`cared_today` and return
      - unfed: increment `consecutive_unfed`; at >= 2 the animal escapes
        (`animal = None`, counters/fertilizer reset) and return
      - fed: reset `consecutive_unfed` to 0
      - fed AND cared: bank +1 `pending_care_bonus` (capped by max_held - yield)
      - surviving animals: set `fertilizer_available = 1` (no accumulate)
      - reset `fed_today` / `cared_today` for the new day
    """
    if tile.animal is None:
        tile.fed_today = False
        tile.cared_today = False
        return

    # Consecutive unfed: two misses → escape (animal removed, structure stays).
    if not tile.fed_today:
        tile.consecutive_unfed += 1
        if tile.consecutive_unfed >= 2:
            tile.animal = None
            tile.consecutive_unfed = 0
            tile.fed_today = False
            tile.cared_today = False
            tile.fertilizer_available = 0
            return
    else:
        tile.consecutive_unfed = 0

    # Bank care bonus if both fed and cared today (capped by max_held - yield).
    if tile.fed_today and tile.cared_today:
        max_held = ANIMAL_CONFIG[tile.animal]["max_held"]
        if tile.yield_units < max_held:
            tile.pending_care_bonus += 1

    # Surviving animals make 1 fertilizer available at end of day (no accumulate).
    tile.fertilizer_available = 1
    tile.fed_today = False
    tile.cared_today = False