from src.models.game import RealityState
from src.utils.config import TURNS_PER_DAY
from src.models.crops import CROP_CONFIG
from src.models.action import PlantActionState, ActionState
from src.models.farm import PlantState
from src.models.resource import ResourceState
from src.utils.farm import in_bounds
from src.domains.farm.production import crop_future_yield, crop_window_days_remaining


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
    max_lifespan_step = state.step + (cfg.max_yield_day + 1) * TURNS_PER_DAY

    farm.tiles[row][col] = PlantState(
        crop=action.crop,
        planted_day=state.day,
        max_lifespan_step=max_lifespan_step,
    )
    return {"crop": action.crop, "position": [row, col], "planted": True}


def get_valid_plant_actions_for(player: RealityState, unit_pos) -> list[PlantActionState]:
    """Valid PLANT actions for a unit at `unit_pos` ([row, col]).

    A PLANT of crop C is valid iff the unit is in bounds, the tile is empty
    (`None`), and the player has at least one C seed. Returns one
    `PlantActionState` per crop with seeds > 0.
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    if farm.tiles[row][col] is not None:
        return []
    seeds = player.private.seeds
    return [
        PlantActionState(type="PLANT", crop=crop)
        for crop in type(seeds).model_fields
        if getattr(seeds, crop, 0) > 0
    ]


def plant_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """PLANT consumes one seed (valued at seed_cost), one empty tile, and one step."""
    return ResourceState(
        STEP=1.0,
        SEED=float(CROP_CONFIG[action.crop].seed_cost),
        LAND=1.0,
    )


def plant_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY from harvesting + selling the crop's achievable yield,
    plus PRODUCE units (raw yield count moved into the shed)."""
    cfg = CROP_CONFIG[action.crop]
    if cfg.yield_type != "one-time":
        return ResourceState()
    yield_units = crop_future_yield(action.crop, player.day)
    return ResourceState(
        MONEY=float(yield_units * getattr(player.market.prices, action.crop, 0)),
        PRODUCE=float(yield_units),
    )


def plant_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream steps the player must spend to realize the future gain:
    one water per remaining window day, plus one harvest and one sell."""
    cfg = CROP_CONFIG[action.crop]
    if cfg.yield_type != "one-time":
        return ResourceState()
    waters = crop_window_days_remaining(action.crop, player.day, player.day)
    return ResourceState(STEP=float(waters + 2))
