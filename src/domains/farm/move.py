from src.models.action import MOVE_ACTIONS

# [row, column] deltas — farm.farmer is [row, column] per FarmState.
_MOVE_DELTAS = {
    "NORTH": (-1, 0),
    "SOUTH": (1, 0),
    "EAST": (0, 1),
    "WEST": (0, -1),
}


def move_unit(farm, unit_pos, direction: MOVE_ACTIONS) -> dict:
    """Move `unit_pos` ([row, column]) one tile, clamped to the grid bounds.

    Locked tiles are passable — units can cross unbought quadrants but cannot
    act there, so only grid bounds apply here. The position list is mutated in
    place; out-of-bounds moves are silently ignored.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"from": None, "to": None, "moved": False}

    delta = _MOVE_DELTAS.get(direction)
    if delta is None:
        return {"from": list(unit_pos), "to": list(unit_pos), "moved": False}

    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    dr, dc = delta
    nr, nc = unit_pos[0] + dr, unit_pos[1] + dc

    from_pos = list(unit_pos)
    if 0 <= nr < rows and 0 <= nc < cols:
        unit_pos[0] = nr
        unit_pos[1] = nc
        return {"from": from_pos, "to": [nr, nc], "moved": True}
    return {"from": from_pos, "to": from_pos, "moved": False}