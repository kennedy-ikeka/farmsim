"""Action scoring — cost / reward / risk scores for valid actions.

Cost score = sum((usage / available) * weight) for each consumed resource.
Reward and risk scores are stubbed to 0 (TODO).
Final score = reward - (cost + risk) / 2  →  -cost / 2 for now.
"""
from src.utils.config import EPISODE_STEPS
from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG
from src.domains.market.buy_land import QUADRANT_COST, QUADRANT_ORDER
from src.domains.market.hire import FARM_HAND_COST_MULT, _fib
from src.models.farm import AnimalState
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
    t = action.type

    if t == "PLANT":
        usage["SEED"] = 1.0
    elif t == "BUILD_COOP":
        usage["LAND"] = 1.0
    elif t == "BUILD_PASTURE":
        usage["LAND"] = 1.0
    elif t == "BUY_SEED":
        usage["MONEY"] = float(action.count * CROP_CONFIG[action.crop].seed_cost)
    elif t == "BUY_PRODUCT":
        usage["MONEY"] = float(action.count * getattr(player.market.prices, action.item))
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


def cost_score(action: ActionState, player: RealityState) -> float:
    usage = action_resource_usage(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (usage[r] / max(avail[r], 1.0)) * getattr(weights, r)
        for r in usage if usage[r] > 0
    )


def reward_score(action: ActionState, player: RealityState) -> float:
    return 0.0  # TODO


def risk_score(action: ActionState, player: RealityState) -> float:
    return 0.0  # TODO


def score_action(action: ActionState, player: RealityState) -> ScoredActionState:
    cost = cost_score(action, player)
    reward = reward_score(action, player)
    risk = risk_score(action, player)
    score = reward - (cost + risk) / 2
    return ScoredActionState(
        action=action, score=score,
        cost_score=cost, reward_score=reward, risk_score=risk,
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