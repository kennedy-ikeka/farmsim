"""End-of-day plant refresh — miss counters, weed conversion, decay.

Runs at day rollover for every plant tile. The planting day counts as the first
unwatered day; two consecutive missed end-of-day refreshes turn the plant into
a weed. Past `max_lifespan_step`, `yield_units` decays by 1 every other turn;
at 0 the plant becomes a weed.
"""
from src.models.farm import FarmState, PlantState, WeedState
from src.models.game import GameState


def refresh_plant(state: GameState, farm: FarmState, r: int, c: int,
                  tile: PlantState) -> None:
    """Advance a plant tile's end-of-day state in place.

    Mutates `tile` (and may reassign `farm.tiles[r][c]` to a `WeedState`):
      - increments `consecutive_unwatered` if not watered today, else resets to 0
      - resets `watered_today` to False for the new day
      - converts to a weed if `consecutive_unwatered >= 2`
      - past `max_lifespan_step`, decays `yield_units` by 1 every other turn
      - converts to a weed when decayed to 0 yield
    """
    # Consecutive unwatered: planting day counts as the first miss (starts at 1).
    if not tile.watered_today:
        tile.consecutive_unwatered += 1
    else:
        tile.consecutive_unwatered = 0
    tile.watered_today = False

    # Neglected two days in a row → weed.
    if tile.consecutive_unwatered >= 2:
        farm.tiles[r][c] = WeedState()
        return

    # Decay: past max_lifespan_step, yield_units drops by 1 every other turn.
    if state.step > tile.max_lifespan_step:
        if (state.step - tile.max_lifespan_step) % 2 == 1:
            tile.yield_units = max(0, tile.yield_units - 1)
        if tile.yield_units <= 0:
            farm.tiles[r][c] = WeedState()