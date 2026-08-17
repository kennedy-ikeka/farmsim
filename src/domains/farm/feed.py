from src.models.farm import AnimalState
from src.models.action import FeedActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState
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


def feed_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """FEED consumes one WHEAT (valued at the market price) and one step.
    PRODUCE tracks the raw WHEAT unit consumed from the shed."""
    return ResourceState(
        STEP=1.0,
        MONEY=float(getattr(player.market.prices, "WHEAT", 0)),
        PRODUCE=1.0,
    )


def feed_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY: feeding preserves one base production unit's worth of
    the animal's product (valued at its market price). PRODUCE = 1 product unit."""
    farm = player.farms[player.player]
    tile = tile_at(farm, farm.farmer)
    if isinstance(tile, AnimalState) and tile.animal is not None:
        product = ANIMAL_CONFIG[tile.animal].product
        return ResourceState(
            MONEY=float(getattr(player.market.prices, product, 0)),
            PRODUCE=1.0,
        )
    return ResourceState()


def feed_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream steps to realize the gain: one harvest + one sell."""
    return ResourceState(STEP=2.0)