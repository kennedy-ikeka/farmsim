"""End-of-day animal refresh — escape checks, care bonus banking, production.

Runs at day rollover for every animal-structure tile. Two consecutive missed
feeds cause the animal to escape (animal removed, structure stays empty). Fed-
and-cared animals bank a `pending_care_bonus` (capped by `max_held - yield`).
On scheduled production days (placement_day + first_yield_day + k*interval),
the animal produces its product: base 1 unit always, plus the banked
`pending_care_bonus` if it was fed today (the bank resets to 0 either way).
`yield_units` is capped by `max_held`. Surviving animals make 1 fertilizer
available at end of day.
"""
from src.models.animals import ANIMAL_CONFIG
from src.models.farm import AnimalState
from src.models.game import GameState


def refresh_animal(tile: AnimalState, state: "GameState | None" = None) -> None:
    """Advance an animal-structure tile's end-of-day state in place.

    Mutates `tile` directly (never reassigns the slot — the structure stays):
      - empty structures: reset `fed_today`/`cared_today` and return
      - unfed: increment `consecutive_unfed`; at >= 2 the animal escapes
        (`animal = None`, counters/fertilizer reset) and return
      - fed: reset `consecutive_unfed` to 0
      - fed AND cared: bank +1 `pending_care_bonus` (capped by max_held - yield)
      - scheduled production day: produce base 1 + banked bonus (if fed today),
        cap `yield_units` at `max_held`, reset `pending_care_bonus` to 0
      - surviving animals: set `fertilizer_available = 1` (no accumulate)
      - reset `fed_today` / `cared_today` for the new day

    `state` is needed only for the scheduled-production payout (it reads
    `state.day` against `tile.placed_day`); it's optional so existing callers
    that only exercise escape/banking/fertilizer behaviour need not supply it.
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
        max_held = ANIMAL_CONFIG[tile.animal].max_held
        if tile.yield_units < max_held:
            tile.pending_care_bonus += 1

    # Scheduled production: on placement_day + first_yield_day + k*interval,
    # produce base 1 + banked bonus (fed today) into yield_units, reset bank.
    if state is not None and tile.placed_day is not None:
        cfg = ANIMAL_CONFIG[tile.animal]
        dsp = state.day - tile.placed_day
        if dsp >= cfg.first_yield_day and (dsp - cfg.first_yield_day) % cfg.interval == 0:
            produced = 1 + (tile.pending_care_bonus if tile.fed_today else 0)
            tile.yield_units = min(cfg.max_held, tile.yield_units + produced)
            tile.pending_care_bonus = 0  # bank resets on a production day

    # Surviving animals make 1 fertilizer available at end of day (no accumulate).
    tile.fertilizer_available = 1
    tile.fed_today = False
    tile.cared_today = False