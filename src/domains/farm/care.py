from src.models.farm import AnimalState


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