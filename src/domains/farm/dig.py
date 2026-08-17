from src.models.action import DigActionState, ActionState
from src.models.farm import PlantState, WeedState, AnimalState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.utils.farm import in_bounds


def dig(farm, unit_pos, action: DigActionState) -> dict:
    """Dig the unit's current tile, removing a plant, weed, or empty structure.

    No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the target tile is empty (None) or locked ("LOCKED")
      - the target tile is an animal structure that currently houses an animal

    On success, clears the tile to None (empty unlocked). Digging a plant
    does not yield any produce — use HARVEST to collect accumulated yield
    first.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "cleared": False, "kind": None}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "cleared": False, "kind": None}

    tile = farm.tiles[row][col]
    if tile is None or tile == "LOCKED":
        return {"position": [row, col], "cleared": False, "kind": None}  # nothing to dig

    if isinstance(tile, AnimalState):
        if tile.animal is not None:
            return {"position": [row, col], "cleared": False, "kind": tile.kind}  # animal in the way
        farm.tiles[row][col] = None
        return {"position": [row, col], "cleared": True, "kind": tile.kind}

    # Plant or weed — removable.
    if isinstance(tile, (PlantState, WeedState)):
        kind = "PLANT" if isinstance(tile, PlantState) else "WEED"
        farm.tiles[row][col] = None
        return {"position": [row, col], "cleared": True, "kind": kind}
    return {"position": [row, col], "cleared": False, "kind": None}


def get_valid_dig_actions_for(farm, unit_pos) -> list[DigActionState]:
    """Valid DIG actions for a unit at `unit_pos` ([row, col]).

    DIG is valid iff the unit is in bounds and the tile is a plant, a weed, or
    an empty (animal-less) structure. Empty tiles, locked tiles, and occupied
    structures are not diggable.
    """
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    tile = farm.tiles[row][col]
    if tile is None or tile == "LOCKED":
        return []
    if isinstance(tile, (PlantState, WeedState)):
        return [DigActionState(type="DIG")]
    if isinstance(tile, AnimalState) and tile.animal is None:
        return [DigActionState(type="DIG")]
    return []


def dig_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    """DIG clears an occupied tile, yielding one empty land tile."""
    return ResourceState(LAND=1.0)