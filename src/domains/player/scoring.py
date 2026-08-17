"""Action scoring — scarcity-weighted cost / reward / future scores.

Cost score   = sum((usage / max(available, 1))              * weight)
Reward score = sum((gain  / max(available + gain, 1))       * weight)
Future cost / future reward = same, over the deferred usage / gain.
Final score = (reward - cost) + (future_reward - future_cost) * FUTURE_DISCOUNT_RATE.

Scarcity weighting means spending a resource hurts more when you have little
of it (cost is the fraction of available stock consumed), and gaining a
resource is worth less when you already have plenty (reward has diminishing
returns via the `available + gain` denominator). This creates the pressure
the planner needs: after a buy drains money, subsequent buys become
expensive (smaller available → larger cost fraction) while sells become
attractive (smaller available → larger reward fraction), pushing the agent
to produce and sell rather than buy until broke.

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


def cost_score(action: ActionState, player: RealityState) -> float:
    """Scarcity-weighted cost: fraction of available stock consumed.

    `usage / max(available, 1)` — spending 500 from 3000 costs 0.17,
    but spending 500 from 500 costs 1.0. This makes buys progressively
    more expensive as the bank drains, naturally capping spending.
    """
    usage = action_resource_usage(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (getattr(usage, r) / max(getattr(avail, r), 1.0)) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(usage, r) > 0
    )


def reward_score(action: ActionState, player: RealityState) -> float:
    """Scarcity-weighted reward with diminishing returns.

    `gain / max(available + gain, 1)` — the marginal value of gaining `gain`
    when you already have `available`. Earning 100 when broke (avail=100)
    gives 0.5; earning 100 when rich (avail=3000) gives 0.03. This pushes
    the agent to produce and sell when money is scarce.
    """
    gain = action_resource_gain(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (getattr(gain, r) / max(getattr(avail, r) + getattr(gain, r), 1.0)) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(gain, r) > 0
    )


def future_cost_score(action: ActionState, player: RealityState) -> float:
    """Scarcity-weighted future cost (same formula as cost_score, over future usage)."""
    usage = action_future_usage(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (getattr(usage, r) / max(getattr(avail, r), 1.0)) * getattr(weights, r)
        for r in _RESOURCE_FIELDS if getattr(usage, r) > 0
    )


def future_reward_score(action: ActionState, player: RealityState) -> float:
    """Scarcity-weighted future reward (same formula as reward_score, over future gain)."""
    gain = action_future_gain(action, player)
    avail = available_resources(player)
    weights = player.private.config.resource_weights
    return sum(
        (getattr(gain, r) / max(getattr(avail, r) + getattr(gain, r), 1.0)) * getattr(weights, r)
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


def update_resource_weights(player: RealityState, selected: list[ScoredActionState]) -> None:
    """Satiation-style weight update after an action is played.

    For each selected action, compute the unweighted per-resource *immediate*
    net contribution = gain - usage. Resources with positive immediate net
    are the "drivers" — they motivated the choice right now. Each driver's
    weight is reduced by a flat `lr`, so the resource that drove the last
    action is less influential during the next planning.

    Only *immediate* drivers are satiated — future-only drivers (e.g. PRODUCE
    after BUY_ANIMAL, where the gain is realized downstream) keep their
    weight so the agent keeps prioritizing them until the produce actually
    flows.

    Designed to be called once per selected action (not once per turn) so the
    reduction accumulates across consecutive selections within the same play.
    """
    if not selected:
        return
    config = player.private.config
    lr = config.weight_learning_rate

    weights = config.resource_weights
    for s in selected:
        usage = action_resource_usage(s.action, player)
        gain = action_resource_gain(s.action, player)
        for r in _RESOURCE_FIELDS:
            # Immediate-only drivers: a resource that the action *gains* more
            # of than it *uses* drove the choice. Future-only drivers (e.g.
            # PRODUCE after BUY_ANIMAL) are NOT satiated, so the next plan
            # still prioritizes them.
            immediate_net = getattr(gain, r) - getattr(usage, r)
            if immediate_net > 0:
                setattr(weights, r, max(getattr(weights, r) - lr, 0.0))