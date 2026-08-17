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
`ResourceState` fields and multiply each by the matching `resource_needs`
field.

`resource_needs` is not learned — it is regenerated from the current
production-pipeline state before each play by `generate_resource_needs`.
Each need is a 0/1 bottleneck flag: resources you have the means to produce
but lack (e.g. PRODUCE when animals are placed but the shed is empty) get
need 1.0, so the scoring pressure focuses on whatever stage is currently
under-supplied.
"""
from typing import get_args

from src.models.action import ActionState
from src.models.game import RealityState
from src.models.scoring import ScoredActionState, ScoredValidStepsState
from src.models.environment import ValidStepsState


def evaluate_state(player: RealityState) -> float:
    ...


def score_action(action: ActionState, player: RealityState) -> ScoredActionState:
    before = evaluate_state(player)

    sim = player.model_copy(deep=True)
    after = evaluate_state(sim)
    return ScoredActionState()


def score_valid_actions(valid_steps: ValidStepsState, player: RealityState) -> ScoredValidStepsState:
    """Score every action in a ValidStepsState."""
    farmer = [score_action(a, player) for a in valid_steps.farmer]
    hands = [
        [score_action(a, player) for a in hand_actions]
        for hand_actions in valid_steps.hands
    ]
    market = [score_action(a, player) for a in valid_steps.market]
    return ScoredValidStepsState(farmer=farmer, hands=hands, market=market)
