from src.models.farm import AnimalState
from src.models.action import BuildCoopActionState, BuildPastureActionState, ActionState
from src.models.resource import ResourceState
from src.models.game import RealityState
from src.models.animals import ANIMAL_CONFIG
from src.utils.farm import in_bounds
from src.domains.farm.production import animal_future_production, EPISODE_DAYS


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


def build_structure_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    """BUILD_COOP / BUILD_PASTURE consume one empty tile and one step."""
    return ResourceState(STEP=1.0, LAND=1.0)


def build_structure_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    """Deferred MONEY from the animal the structure will house under optimal
    completion: BUILD_COOP → goose production; BUILD_PASTURE → the better of
    COW vs SHEEP by gross production value. PRODUCE = future product +
    fertilizer units (raw count of sellable goods produced)."""
    prices = player.market.prices
    day = player.day
    if action.type == "BUILD_COOP":
        y, f = animal_future_production("GOOSE", day)
        return ResourceState(
            MONEY=float(y * getattr(prices, "EGG", 0) + f * getattr(prices, "FERTILIZER", 0)),
            PRODUCE=float(y + f),
        )
    # BUILD_PASTURE — pick the better of COW vs SHEEP.
    best = 0.0
    best_produce = 0.0
    for animal in ("COW", "SHEEP"):
        y, f = animal_future_production(animal, day)
        product = ANIMAL_CONFIG[animal].product
        value = y * getattr(prices, product, 0) + f * getattr(prices, "FERTILIZER", 0)
        if value > best:
            best = value
            best_produce = y + f
    return ResourceState(MONEY=float(best), PRODUCE=float(best_produce))


def build_structure_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    """Downstream spend to realize the future gain: place + daily feed + daily
    care + 1 harvest + 1 sell + daily collect (steps), plus daily feed wheat
    (MONEY) and the feed wheat as PRODUCE units consumed from the shed."""
    remaining_days = max(0, EPISODE_DAYS - player.day)
    prices = player.market.prices
    return ResourceState(
        STEP=float(1 + remaining_days + remaining_days + 1 + 1 + remaining_days),
        MONEY=float(remaining_days * getattr(prices, "WHEAT", 0)),
        PRODUCE=float(remaining_days),
    )