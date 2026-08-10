from src.models.action import PlaceActionState
from src.models.farm import AnimalState
from src.utils.farm import ensure_inventory, is_shed_adjacent, place_animal


SHED_CAPACITY = 100

# Which structure kind each animal is placed on.
_ANIMAL_STRUCTURE = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}


def place(state, farm, unit_pos, action: PlaceActionState, inv_index: int) -> dict:
    """Place `item` from the unit's inventory onto a tile or into the shed.

    Two modes, tried in order:

      1. Animal placement — standing on a matching *unoccupied* structure
         (GOOSE on a coop, COW/SHEEP on a pasture) places one animal from
         inventory onto the tile. The `count` argument is ignored; exactly
         one animal is placed. The tile's animal-related fields are reset so
         the newly placed animal starts fresh (`consecutive_unfed = 0`,
         per the README's "survives its first day unfed" rule).

      2. Shed drop — standing orthogonally adjacent to the shed moves up to
         `count` of `item` from inventory into the shed, capped by
         `SHED_CAPACITY`; excess stays in inventory.

    No-ops (silent) when the unit position is malformed/out of bounds, or
    neither mode applies (not on a matching structure and not shed-adjacent,
    or the item is invalid, or there is nothing to move).
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "item": action.item, "count": 0, "mode": None}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "item": action.item, "count": 0, "mode": None}

    item = action.item
    inventory = ensure_inventory(state, inv_index)
    tile = farm.tiles[row][col]

    # 1. Animal placement — item is an animal and the tile is a matching,
    #    unoccupied structure, with the animal available in inventory.
    if (item in _ANIMAL_STRUCTURE
            and isinstance(tile, AnimalState)
            and tile.kind == _ANIMAL_STRUCTURE[item]
            and tile.animal is None
            and inventory.get(item, 0) > 0):
        place_animal(tile, item, state.day, inventory)
        return {"position": [row, col], "item": item, "count": 1, "mode": "animal"}

    # 2. Shed drop — unit is orthogonally adjacent to the shed.
    if not is_shed_adjacent(row, col, rows, cols):
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    shed = state.private.shed
    if item not in type(shed).model_fields:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}  # not a valid shed item

    have = inventory.get(item, 0)
    if have <= 0:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    total_in_shed = sum(getattr(shed, f) for f in type(shed).model_fields)
    space = max(0, SHED_CAPACITY - total_in_shed)
    to_move = min(action.count, have, space)
    if to_move <= 0:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    setattr(shed, item, getattr(shed, item, 0) + to_move)
    inventory[item] = have - to_move
    return {"position": [row, col], "item": item, "count": to_move, "mode": "shed"}