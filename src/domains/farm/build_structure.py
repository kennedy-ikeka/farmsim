from src.models.farm import AnimalState


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