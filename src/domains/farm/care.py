from src.models.farm import AnimalState
from src.models.action import CareActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.models.animals import ANIMAL_CONFIG
from src.utils.farm import in_bounds, tile_at


def care(farm, unit_pos, action) -> dict:
    """Mark a housed animal cared-for today (once per day).

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not an animal structure
      - no animal is housed on the structure
      - the animal has already been cared for today

    On success, sets `cared_today = True`. The bonus is banked at end-of-day
    only if the animal was also fed that day (basic needs first).
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "animal": None, "cared": False}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "animal": None, "cared": False}

    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState):
        return {"position": [row, col], "animal": None, "cared": False}
    if tile.animal is None:
        return {"position": [row, col], "animal": None, "cared": False}
    if tile.cared_today:
        return {"position": [row, col], "animal": tile.animal, "cared": False}  # only once per day

    tile.cared_today = True
    return {"position": [row, col], "animal": tile.animal, "cared": True}


def get_valid_care_actions_for(farm, unit_pos) -> list[CareActionState]:
    """Valid CARE actions for a unit at `unit_pos` ([row, col]).

    Valid iff the unit is in bounds, the tile is an occupied animal structure
    that hasn't been cared for today.
    """
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState) or tile.animal is None:
        return []
    if tile.cared_today:
        return []
    return [CareActionState(type="CARE")]


def care_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY: caring banks one bonus production unit's worth of the
    animal's product (valued at its market price). PRODUCE = 1 product unit."""
    farm = player.farms[player.player]
    tile = tile_at(farm, farm.farmer)
    if isinstance(tile, AnimalState) and tile.animal is not None:
        product = ANIMAL_CONFIG[tile.animal].product
        return ResourceState(
            MONEY=float(getattr(player.market.prices, product, 0)),
            PRODUCE=1.0,
        )
    return ResourceState()


def care_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream steps to realize the gain: one harvest + one sell."""
    return ResourceState(STEP=2.0)