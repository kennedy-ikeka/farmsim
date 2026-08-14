from src.utils.farm import ensure_inventory, is_shed_adjacent, in_bounds
from src.models.action import PickupActionState


def pickup(state, farm, unit_pos, action: PickupActionState, inv_index: int) -> dict:
    """Pick up to `count` of `item` from the shed into the unit's inventory.

    The unit must be orthogonally adjacent to the shed (one of the four center
    tiles). No-ops (silent) when:
      - the unit position is malformed or out of bounds
      - the unit is not shed-adjacent
      - the item is not a valid shed field (e.g. seeds, which live in a
        separate slot and are never picked up)
      - there is none of the item in the shed

    On success, moves min(count, shed[item]) units from the shed into the
    unit's inventory (the `inv_index`-th dict in `private.inventories`).
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return {"position": None, "item": action.item, "count": 0}

    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not (0 <= row < rows and 0 <= col < cols):
        return {"position": None, "item": action.item, "count": 0}

    if not is_shed_adjacent(row, col, rows, cols):
        return {"position": [row, col], "item": action.item, "count": 0}

    shed = state.privates[state.player].shed
    item = action.item
    if item not in type(shed).model_fields:
        return {"position": [row, col], "item": item, "count": 0}  # not a valid shed item

    available = getattr(shed, item, 0)
    if available <= 0:
        return {"position": [row, col], "item": item, "count": 0}

    to_move = min(action.count, available)
    setattr(shed, item, available - to_move)

    inventory = ensure_inventory(state, inv_index)
    setattr(inventory, item, getattr(inventory, item, 0) + to_move)
    return {"position": [row, col], "item": item, "count": to_move}


def get_valid_pickup_actions_for(player, unit_pos, inv_index) -> list[PickupActionState]:
    """Valid PICKUP actions for a unit at `unit_pos` ([row, col]).

    The unit must be orthogonally adjacent to the shed. Returns one
    `PickupActionState(item=I, count=1)` per shed field `I` with quantity > 0
    (seeds live in a separate slot and are never picked up).
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if not is_shed_adjacent(row, col, rows, cols):
        return []
    shed = player.private.shed
    return [
        PickupActionState(type="PICKUP", item=item, count=1)
        for item in type(shed).model_fields
        if getattr(shed, item, 0) > 0
    ]