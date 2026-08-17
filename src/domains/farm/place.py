from src.models.game import RealityState
from src.models.action import (
    ActionState, PlaceActionState, SellActionState,
)
from src.models.farm import AnimalState
from src.models.player import InventoryState
from src.models.animals import ANIMAL_CONFIG
from src.utils.farm import ensure_inventory, is_shed_adjacent, place_animal, in_bounds
from src.domains.farm.production import animal_pipeline


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
            and getattr(inventory, item, 0) > 0):
        place_animal(tile, item, state.day, inventory)
        return {"position": [row, col], "item": item, "count": 1, "mode": "animal"}

    # 2. Shed drop — unit is orthogonally adjacent to the shed.
    if not is_shed_adjacent(row, col, rows, cols):
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    shed = state.privates[state.player].shed
    if item not in type(shed).model_fields:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}  # not a valid shed item

    have = getattr(inventory, item, 0)
    if have <= 0:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    total_in_shed = sum(getattr(shed, f) for f in type(shed).model_fields)
    space = max(0, SHED_CAPACITY - total_in_shed)
    to_move = min(action.count, have, space)
    if to_move <= 0:
        return {"position": [row, col], "item": item, "count": 0, "mode": None}

    setattr(shed, item, getattr(shed, item, 0) + to_move)
    setattr(inventory, item, have - to_move)
    return {"position": [row, col], "item": item, "count": to_move, "mode": "shed"}


def get_valid_place_actions_for(player, unit_pos, inv_index) -> list[PlaceActionState]:
    """Valid PLACE actions for a unit at `unit_pos` ([row, col]).

    PLACE has two modes (tried in order by `place`):
      1. Animal placement — standing on a matching unoccupied structure with
         that animal in the unit's inventory.
      2. Shed drop — standing shed-adjacent, dropping a shed-item from the
         unit's inventory into the shed (capped by `SHED_CAPACITY`).

    Returns one `PlaceActionState(item=I, count=1)` per item in the unit's
    inventory for which either mode would fire.
    """
    farm = player.farms[player.player]
    rc = in_bounds(farm, unit_pos)
    if rc is None:
        return []
    row, col = rc
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0

    # Ensure the unit's inventory slot exists (mirrors `place`'s first step).
    inventories = player.private.inventories
    while len(inventories) <= inv_index:
        inventories.append(InventoryState())
    inventory = inventories[inv_index]

    tile = farm.tiles[row][col]
    shed = player.private.shed
    shed_full = sum(getattr(shed, f) for f in type(shed).model_fields) >= SHED_CAPACITY
    shed_adjacent = is_shed_adjacent(row, col, rows, cols)

    actions: list[PlaceActionState] = []
    seen = set()
    for item in type(inventory).model_fields:
        have = getattr(inventory, item, 0)
        if have <= 0 or item in seen:
            continue
        seen.add(item)
        # Mode 1 — animal placement.
        if (item in _ANIMAL_STRUCTURE
                and isinstance(tile, AnimalState)
                and tile.kind == _ANIMAL_STRUCTURE[item]
                and tile.animal is None):
            actions.append(PlaceActionState(type="PLACE", item=item, count=1))
            continue
        # Mode 2 — shed drop.
        if (shed_adjacent
                and item in type(shed).model_fields
                and not shed_full):
            actions.append(PlaceActionState(type="PLACE", item=item, count=1))
    return actions


def get_place_pipeline(action: PlaceActionState, player: RealityState,
                       unit_pos=None, inv_index: int = 0) -> list[ActionState]:
    """Actions following a PLACE: an animal placement starts the animal's
    per-day care + harvest + sell tail; a shed drop is realized by SELLING the
    dropped item.
    """
    if action.item in ANIMAL_CONFIG:
        return animal_pipeline(action.item, player.day)
    return [SellActionState(type="SELL", item=action.item, count=action.count)]