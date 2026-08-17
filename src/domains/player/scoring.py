"""Action scoring — cost / reward / future scores for valid actions.

Cost score = sum(usage * weight) for each consumed resource.
Reward score = sum(gain * weight) for each gained resource.
Future cost / future reward = same, over the deferred usage / gain.
Final score = (reward - cost) + (future_reward - future_cost) * FUTURE_DISCOUNT_RATE.

Per-action usage / gain / future_gain / future_usage live in the farm and
market action modules (`src/domains/farm/<action>.py`,
`src/domains/market/<action>.py`). The farm / market scoring modules
(`src/domains/farm/scoring.py`, `src/domains/market/scoring.py`) hold the
registries that dispatch by `action.type`. The four `action_*` wrappers here
route farm action types to the farm dispatch and market action types to the
market dispatch, then the cost / reward / future scores iterate the
`ResourceState` fields and multiply each by the matching `ResourceWeights`
field.
"""
from typing import get_args

from src.models.action import ActionState, MARKET_ACTIONS
from src.models.game import RealityState
from src.models.resource import ResourceState
from src.models.scoring import ScoredActionState, ScoredValidStepsState
from src.models.environment import ValidStepsState
from src.domains.farm.scoring import (
    farm_resource_usage,
    farm_resource_gain,
    farm_future_gain,
    farm_future_usage,
    available_resources,
)
from src.domains.market.scoring import (
    market_resource_usage,
    market_resource_gain,
    market_future_gain,
    market_future_usage,
)

_MARKET_TYPES = set(get_args(MARKET_ACTIONS))
_RESOURCE_FIELDS = tuple(ResourceState.model_fields)


def action_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_resource_usage(action, player)
    return farm_resource_usage(action, player)


def action_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_resource_gain(action, player)
    return farm_resource_gain(action, player)


def action_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_future_gain(action, player)
    return farm_future_gain(action, player)


def action_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_future_usage(action, player)
    return farm_future_usage(action, player)


def scarcity_score(action: ActionState, player: RealityState) -> float:
    """Scarcity-weighted cost: sum((usage / max(available, 1)) * weight)."""
    usage = action_resource_usage(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (getattr(usage, r) / max(getattr(avail, r), 1.0)) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(usage, r) > 0
    )


def cost_score(action: ActionState, player: RealityState) -> float:
    usage = action_resource_usage(action, player)
    weights = player.private.config.resource_weights
    return sum(
        getattr(usage, r) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(usage, r) > 0
    )


def reward_score(action: ActionState, player: RealityState) -> float:
    gain = action_resource_gain(action, player)
    weights = player.private.config.resource_weights
    return sum(
        getattr(gain, r) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(gain, r) > 0
    )


def future_cost_score(action: ActionState, player: RealityState) -> float:
    usage = action_future_usage(action, player)
    weights = player.private.config.resource_weights
    return sum(
        getattr(usage, r) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(usage, r) > 0
    )


def future_reward_score(action: ActionState, player: RealityState) -> float:
    gain = action_future_gain(action, player)
    weights = player.private.config.resource_weights
    return sum(
        getattr(gain, r) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(gain, r) > 0
    )


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
        cost_score=cost, reward_score=reward,
        future_cost_score=future_cost, future_reward_score=future_reward,
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