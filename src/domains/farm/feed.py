from src.models.farm import AnimalState


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