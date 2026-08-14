from src.models.farm import AnimalState
from src.models.action import BuildCoopActionState, BuildPastureActionState
from src.utils.farm import in_bounds


def build_structure(farm, unit_pos, action) -> dict:
    """Erect a coop or pasture on an empty unlocked tile.

    The structure kind (COOP vs PASTURE) is taken from the action's `type`
    tag. No-ops (silent) when the unit position is malformed or out of
    bounds, or the target tile is occupied (LOCKED, plant, weed, or an
    existing structure) — only a None tile is buildable.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "kind": None, "built": False}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "kind": None, "built": False}

    if farm.tiles[row][col] is not None:
        return {"position": [row, col], "kind": None, "built": False}  # only an empty unlocked tile is buildable

    kind = action.type[len("BUILD_"):]  # BUILD_COOP -> COOP, BUILD_PASTURE -> PASTURE
    farm.tiles[row][col] = AnimalState(kind=kind)
    return {"position": [row, col], "kind": kind, "built": True}


def get_valid_build_actions_for(farm, unit_pos) -> list:
    """Valid BUILD_COOP and BUILD_PASTURE actions for a unit at `unit_pos`.

    Both are valid iff the unit is in bounds and the tile is empty (`None`) —
    any occupant (LOCKED, plant, weed, structure) blocks building. Returns
    both action variants when buildable.
    """
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    if farm.tiles[row][col] is not None:
        return []
    return [BuildCoopActionState(type="BUILD_COOP"), BuildPastureActionState(type="BUILD_PASTURE")]