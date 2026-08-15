"""Action scoring — cost / reward / risk scores for valid actions.

Cost score = sum((usage / available) * weight) for each consumed resource.
Reward score = sum((gain / available) * weight) for each gained resource.
Risk score is stubbed to 0 (TODO).
Final score = reward - (cost + risk) / 2.

`action_resource_usage` and `action_resource_gain` are symmetric: the former
lists what an action consumes, the latter what it gains. SELL gains MONEY,
BUY_SEED gains SEED (economic value), BUY_ANIMAL gains ANIMAL (economic
value), BUY_LAND gains LAND (new empty tiles), HIRE gains HAND, HARVEST gains
MONEY (crop sale value from the unit's tile), COLLECT_FERTILIZER gains MONEY
(fertilizer sale value). Enabler actions whose value is deferred — PLANT,
BUILD_*, WATER, FERTILIZE, CARE, FEED, PICKUP, PLACE, MOVE, PASS, DIG,
BUY_PRODUCT — gain nothing here; their payoff is realized by the harvest /
collect / sell they make possible, which is captured on those actions.
"""
from src.utils.config import EPISODE_STEPS
from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG
from src.domains.market.buy_land import QUADRANT_COST, QUADRANT_ORDER
from src.domains.market.hire import FARM_HAND_COST_MULT, _fib
from src.models.farm import AnimalState, PlantState
from src.models.action import ActionState
from src.models.game import RealityState
from src.models.scoring import ScoredActionState, ScoredValidStepsState
from src.models.environment import ValidStepsState

SEED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMAL_FIELDS = ["GOOSE", "COW", "SHEEP"]
RESOURCES = ("MONEY", "STEP", "SEED", "LAND", "ANIMAL", "HAND")


def available_resources(player: RealityState) -> dict[str, float]:
    """Current amount owned of each resource."""
    farm = player.farms[player.player]
    private = player.private

    empty_tiles = sum(1 for row in farm.tiles for tile in row if tile is None)

    # SEED and ANIMAL availability is valued in economic terms (count * unit
    # cost), so a MELON seed (80) counts more than a WHEAT seed (10) and a
    # COW (400) counts more than a GOOSE (300).
    seed_value = sum(
        getattr(private.seeds, c) * CROP_CONFIG[c].seed_cost
        for c in SEED_FIELDS
    )

    animal_value = sum(
        getattr(private.shed, a) * ANIMAL_CONFIG[a].cost
        for a in ANIMAL_FIELDS
    )
    for inv in private.inventories:
        animal_value += sum(
            getattr(inv, a) * ANIMAL_CONFIG[a].cost for a in ANIMAL_FIELDS
        )
    for row in farm.tiles:
        for tile in row:
            if isinstance(tile, AnimalState) and tile.animal is not None:
                animal_value += ANIMAL_CONFIG[tile.animal].cost

    return {
        "MONEY": farm.money,
        "STEP": float(EPISODE_STEPS - player.step),
        "SEED": float(seed_value),
        "LAND": float(empty_tiles),
        "ANIMAL": float(animal_value),
        "HAND": float(len(farm.hands)),
    }


def action_resource_usage(action: ActionState, player: RealityState) -> dict[str, float]:
    """How much of each resource this action consumes."""
    usage = {"STEP": 1.0}
    farm = player.farms[player.player]
    prices = player.market.prices
    t = action.type

    if t == "PLANT":
        usage["SEED"] = float(CROP_CONFIG[action.crop].seed_cost)
        usage["LAND"] = 1.0
    elif t == "BUILD_COOP":
        usage["LAND"] = 1.0
    elif t == "BUILD_PASTURE":
        usage["LAND"] = 1.0
    elif t == "FEED":
        usage["MONEY"] = float(getattr(prices, "WHEAT", 0))
    elif t == "FERTILIZE":
        usage["MONEY"] = float(getattr(prices, "FERTILIZER", 0))
    elif t == "BUY_SEED":
        usage["MONEY"] = float(action.count * CROP_CONFIG[action.crop].seed_cost)
    elif t == "BUY_PRODUCT":
        usage["MONEY"] = float(action.count * getattr(prices, action.item))
    elif t == "BUY_ANIMAL":
        usage["MONEY"] = float(action.count * ANIMAL_CONFIG[action.animal].cost)
    elif t == "HIRE":
        usage["MONEY"] = float(FARM_HAND_COST_MULT * _fib(farm.hires_today))
    elif t == "BUY_LAND":
        next_quad = None
        for q in QUADRANT_ORDER:
            if q not in farm.unlocked_quadrants:
                next_quad = q
                break
        usage["MONEY"] = float(QUADRANT_COST[next_quad]) if next_quad else 0.0

    return usage


def action_resource_gain(action: ActionState, player: RealityState) -> dict[str, float]:
    """How much of each resource this action gains.

    Mirrors `action_resource_usage` for the gain side. Each gain is valued the
    same way the matching availability is valued (raw count for MONEY/LAND/HAND,
    economic value for SEED/ANIMAL), so `(gain / available)` is dimensionless.

    HARVEST and COLLECT_FERTILIZER look up the unit's current tile for the crop
    / animal. `score_action` only receives `(action, player)` — no per-unit
    position — so the farmer's tile (`farm.farmer`) is used. This is exact for
    farmer actions and approximate for hand actions (a hand's HARVEST is scored
    against the farmer's tile, not the hand's); execution is unaffected since
    the action module re-checks the hand's own tile.
    """
    gain: dict[str, float] = {}
    farm = player.farms[player.player]
    prices = player.market.prices
    t = action.type

    if t == "SELL":
        gain["MONEY"] = float(action.count * getattr(prices, action.item, 0))
    elif t == "BUY_SEED":
        gain["SEED"] = float(action.count * CROP_CONFIG[action.crop].seed_cost)
    elif t == "BUY_ANIMAL":
        gain["ANIMAL"] = float(action.count * ANIMAL_CONFIG[action.animal].cost)
    elif t == "BUY_PRODUCT":
        gain["MONEY"] = float(action.count * getattr(prices, action.item, 0))
    elif t == "HIRE":
        gain["HAND"] = 1.0
    elif t == "BUY_LAND":
        next_quad = None
        for q in QUADRANT_ORDER:
            if q not in farm.unlocked_quadrants:
                next_quad = q
                break
        if next_quad is not None:
            rows = len(farm.tiles)
            cols = len(farm.tiles[0]) if rows else 0
            half_r, half_c = rows // 2, cols // 2
            ranges = {
                "NW": (0, half_r, 0, half_c),
                "NE": (0, half_r, half_c, cols),
                "SW": (half_r, rows, 0, half_c),
                "SE": (half_r, rows, half_c, cols),
            }
            r0, r1, c0, c1 = ranges[next_quad]
            gain["LAND"] = float((r1 - r0) * (c1 - c0))
    elif t == "PLANT":
        gain["MONEY"] = float(
            CROP_CONFIG[action.crop].max_yield * getattr(prices, action.crop, 0)
        )
    elif t in ("BUILD_COOP", "BUILD_PASTURE"):
        if t == "BUILD_COOP":
            product = "EGG"
        else:
            product = "MILK" if prices.MILK >= prices.WOOL else "WOOL"
        gain["MONEY"] = float(getattr(prices, product, 0))
    elif t == "FEED":
        tile = _tile_at(farm, farm.farmer)
        if isinstance(tile, AnimalState) and tile.animal is not None:
            product = ANIMAL_CONFIG[tile.animal].product
            gain["MONEY"] = float(getattr(prices, product, 0))
    elif t == "CARE":
        tile = _tile_at(farm, farm.farmer)
        if isinstance(tile, AnimalState) and tile.animal is not None:
            product = ANIMAL_CONFIG[tile.animal].product
            gain["MONEY"] = float(getattr(prices, product, 0))
    elif t == "FERTILIZE":
        tile = _tile_at(farm, farm.farmer)
        if isinstance(tile, PlantState):
            gain["MONEY"] = float(getattr(prices, tile.crop, 0))
    elif t == "WATER":
        tile = _tile_at(farm, farm.farmer)
        if isinstance(tile, PlantState):
            gain["MONEY"] = float(getattr(prices, tile.crop, 0))
    elif t == "DIG":
        gain["LAND"] = 1.0
    elif t == "PLACE":
        if action.item in ANIMAL_CONFIG:
            product = ANIMAL_CONFIG[action.item].product
            gain["MONEY"] = float(getattr(prices, product, 0))
    elif t == "HARVEST":
        tile = _tile_at(farm, farm.farmer)
        if isinstance(tile, PlantState) and tile.yield_units > 0:
            gain["MONEY"] = float(tile.yield_units * getattr(prices, tile.crop, 0))
        elif (isinstance(tile, AnimalState) and tile.animal is not None
                and tile.yield_units > 0):
            product = ANIMAL_CONFIG[tile.animal].product
            gain["MONEY"] = float(tile.yield_units * getattr(prices, product, 0))
    elif t == "COLLECT_FERTILIZER":
        tile = _tile_at(farm, farm.farmer)
        if (isinstance(tile, AnimalState) and tile.animal is not None
                and tile.fertilizer_available > 0):
            gain["MONEY"] = float(getattr(prices, "FERTILIZER", 0))

    return gain


def scarcity_score(action: ActionState, player: RealityState) -> float:
    usage = action_resource_usage(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (usage[r] / max(avail[r], 1.0)) * getattr(weights, r)
        for r in usage if usage[r] > 0
    )


def cost_score(action: ActionState, player: RealityState) -> float:
    usage = action_resource_usage(action, player)
    weights = player.private.config.resource_weights
    return sum(
        usage[r] * getattr(weights, r)
        for r in usage if usage[r] > 0
    )


def reward_score(action: ActionState, player: RealityState) -> float:
    gain = action_resource_gain(action, player)
    weights = player.private.config.resource_weights
    return sum(
        gain[r] * getattr(weights, r)
        for r in gain if gain[r] > 0
    )


def future_cost_score(action: ActionState, player: RealityState) -> float:
    return 0.0


def future_reward_score(action: ActionState, player: RealityState) -> float:
    return 0.0 # TODO


def score_action(action: ActionState, player: RealityState) -> ScoredActionState:
    cost = cost_score(action, player) * player.private.config.score_weights.COST
    reward = reward_score(action, player) * player.private.config.score_weights.REWARD

    future_cost = future_cost_score(action, player) * player.private.config.score_weights.FUTURE_COST
    future_reward = future_reward_score(action, player) * player.private.config.score_weights.FUTURE_REWARD

    immediate_value = reward - cost
    future_value = future_reward - future_cost

    score = immediate_value + (future_value * player.private.config.score_weights.FUTURE_DISCOUNT_RATE)
    return ScoredActionState(
        action=action, score=score,
        cost_score=cost, reward_score=reward, future_cost_score=future_cost,
    )


def score_valid_actions(valid_steps: ValidStepsState, player: RealityState) -> ScoredValidStepsState:
    """Score every action in a ValidStepsState."""
    farmer = [score_action(a, player) for a in valid_steps.farmer]
    hands = [
        [score_action(a, player) for a in hand_actions]
        for hand_actions in valid_steps.hands
    ]
    market = [score_action(a, player) for a in valid_steps.market]
    return ScoredValidStepsState(farmer=farmer, hands=hands, market=market)


def _tile_at(farm, pos):
    """Return the tile at `pos` ([row, col]) or `None` if out of bounds."""
    if not (isinstance(pos, list) and len(pos) == 2):
        return None
    r, c = pos[0], pos[1]
    rows = len(farm.tiles)
    cols = len(farm.tiles[0]) if rows else 0
    if 0 <= r < rows and 0 <= c < cols:
        return farm.tiles[r][c]
    return None
