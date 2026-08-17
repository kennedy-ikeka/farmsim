from src.models.game import RealityState
from src.models.farm import AnimalState
from src.models.action import (
    ActionState, FeedActionState, HarvestActionState, SellActionState,
)
from src.models.animals import ANIMAL_CONFIG
from src.utils.farm import in_bounds, tile_at


def feed(state, farm, unit_pos, action) -> dict:
    """Feed a housed animal one wheat from the shed (once per day).

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is not an animal structure
      - no animal is housed on the structure
      - the animal has already been fed today
      - there is no wheat in the shed

    On success, consumes one WHEAT from `private.shed`, sets `fed_today =
    True`, and resets `consecutive_unfed = 0`.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "animal": None, "fed": False}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "animal": None, "fed": False}

    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState):
        return {"position": [row, col], "animal": None, "fed": False}
    if tile.animal is None:
        return {"position": [row, col], "animal": None, "fed": False}
    if tile.fed_today:
        return {"position": [row, col], "animal": tile.animal, "fed": False}  # only once per day

    shed = state.privates[state.player].shed
    if shed.WHEAT <= 0:
        return {"position": [row, col], "animal": tile.animal, "fed": False}

    shed.WHEAT -= 1
    tile.fed_today = True
    tile.consecutive_unfed = 0
    return {"position": [row, col], "animal": tile.animal, "fed": True}


def get_valid_feed_actions_for(player, unit_pos) -> list[FeedActionState]:
    """Valid FEED actions for a unit at `unit_pos` ([row, col]).

    FEED is valid iff the unit is in bounds, the tile is an occupied animal
    structure that hasn't been fed today, and the player has wheat in the shed.
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if not isinstance(tile, AnimalState) or tile.animal is None:
        return []
    if tile.fed_today:
        return []
    if player.private.shed.WHEAT <= 0:
        return []
    return [FeedActionState(type="FEED")]


def get_feed_pipeline(action: FeedActionState, player: RealityState,
                      unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """Actions following a FEED on an animal tile: HARVEST the animal's
    product and SELL it. Non-animal tiles have no downstream.
    """
    farm = player.farms[player.player]
    tile = tile_at(farm, unit_pos) if unit_pos is not None else None
    if isinstance(tile, AnimalState) and tile.animal is not None:
        product = ANIMAL_CONFIG[tile.animal].product
        pipeline: list[ActionState] = [HarvestActionState(type="HARVEST")]
        if tile.yield_units > 0:
            pipeline.append(SellActionState(type="SELL", item=product, count=tile.yield_units))
        return pipeline
    return []