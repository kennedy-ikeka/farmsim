from src.utils.config import TURNS_PER_DAY
from src.models.crops import CROP_CONFIG
from src.models.action import PlantActionState
from src.models.farm import PlantState


def plant(state, farm, unit_pos, action: PlantActionState) -> dict:
    """Plant `action.crop` on the unit's current tile, consuming one seed.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is occupied (LOCKED, plant, weed, or structure)
      - the player has no seeds of that crop

    On success, decrements `private.seeds[crop]` by one and writes a plant dict
    onto the tile with the fields defined in gameplay/AGENTS.md.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"crop": action.crop, "position": None, "planted": False}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"crop": action.crop, "position": None, "planted": False}

    # Only an empty (None) tile is plantable. LOCKED tiles and any occupied
    # tile (plant / weed / structure) are not None and are rejected.
    if farm.tiles[row][col] is not None:
        return {"crop": action.crop, "position": [row, col], "planted": False}

    seeds = state.privates[state.player].seeds
    available = getattr(seeds, action.crop, 0)
    if available <= 0:
        return {"crop": action.crop, "position": [row, col], "planted": False}

    setattr(seeds, action.crop, available - 1)

    cfg = CROP_CONFIG[action.crop]
    # Decay begins one day after max_yield_day for both one-time and ongoing
    # crops; convert that day to a step (turn) offset from the current step.
    max_lifespan_step = state.step + (cfg["max_yield_day"] + 1) * TURNS_PER_DAY

    farm.tiles[row][col] = PlantState(
        crop=action.crop,
        planted_day=state.day,
        max_lifespan_step=max_lifespan_step,
    )
    return {"crop": action.crop, "position": [row, col], "planted": True}