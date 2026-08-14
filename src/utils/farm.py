from src.models.game import SharedRealityState
from src.models.player import InventoryState


def in_bounds(farm, unit_pos):
    """Return (row, col) if `unit_pos` is a 2-list inside `farm.tiles`, else None.

    Shared guard for every farm-action validity helper — matches the
    malformed-position and out-of-bounds no-op branches that open every
    action implementation in `src.domains.farm`.
    """
    if not (isinstance(unit_pos, list) and len(unit_pos) == 2):
        return None
    row, col = unit_pos[0], unit_pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if 0 <= row < rows and 0 <= col < cols:
        return row, col
    return None


def is_shed_adjacent(row, col, rows, cols):
    """The shed sits at the board center; the four shed-adjacent tiles are
    (half-1, half-1), (half, half-1), (half-1, half), (half, half) where
    half = boardSize // 2 (per board dimension)."""
    half_r = rows // 2
    half_c = cols // 2
    return (row, col) in {
        (half_r - 1, half_c - 1), (half_r, half_c - 1),
        (half_r - 1, half_c), (half_r, half_c),
    }


def ensure_inventory(state: SharedRealityState, inv_index):
    """Return the unit's inventory dict, padding the inventories list with
    empty dicts up to (and including) `inv_index` if needed."""
    inventories = state.privates[state.player].inventories
    while len(inventories) <= inv_index:
        inventories.append(InventoryState())
    return inventories[inv_index]


def place_animal(tile, animal, day, inventory):
    """Place one animal on the structure, resetting the tile to a fresh start."""
    tile.animal = animal
    tile.placed_day = day
    tile.fed_today = False
    tile.consecutive_unfed = 0
    tile.cared_today = False
    tile.yield_units = 0
    tile.fertilizer_available = 0
    tile.pending_care_bonus = 0
    setattr(inventory, animal, getattr(inventory, animal, 0) - 1)
    if getattr(inventory, animal) <= 0:
        setattr(inventory, animal, 0)
