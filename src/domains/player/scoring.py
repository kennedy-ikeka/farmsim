"""Action scoring via state evaluation.

`evaluate_state(player)` projects a player's full state onto a
`ResourceState` — the per-category breakdown of current holdings (MONEY,
STEP, SEED, LAND, ANIMAL, HAND, PRODUCE) measured by `available_resources`.
It is a pure accounting of what the player has right now; `resource_needs`
weighting happens downstream in `score_action`.

`score_action(action, player)` is the delta between the evaluation of the
state before and after the action is applied to a deep copy — actions that
improve the (weighted) resource holdings score positive, actions that
deplete them score negative. Needs gate which resources count: with all
needs at 0, every action scores 0, so `basic_play` falls back to PASS.
Setting needs (e.g. via `generate_resource_needs`) is what activates the
scorer.
"""
from typing import get_args

from src.models.action import ActionState, MARKET_ACTIONS
from src.models.game import RealityState
from src.models.resource import ResourceState
from src.models.scoring import ScoredActionState, ScoredValidStepsState
from src.models.environment import ValidStepsState
from src.domains.player.resource import available_resources
from src.domains.farm.controller import Farm
from src.domains.market.controller import Market

_MARKET_TYPES = set(get_args(MARKET_ACTIONS))


def apply_action(action: ActionState, player: RealityState,
                 unit_pos=None, inv_index: int = 0) -> RealityState:
    """Return a deep copy of `player` with `action` applied.

    Routes farm action types through `Farm.apply` at `unit_pos` (defaulting
    to the active farm's farmer position) and market action types through
    `Market.apply`. PASS returns an unchanged deep copy. Mirrors the
    per-slot dispatch in `Environment.step` so the post-action state matches
    what would actually happen if the action were played in that slot —
    without recording events or advancing the clock.

    `unit_pos` / `inv_index` identify the slot the action is being scored
    for: the farmer is `farm.farmer` with `inv_index=0`; hired hand `k` is
    `farm.hands[k]` with `inv_index=k+1`. They are ignored for market
    actions (which are player-scoped, not position-scoped).

    `unit_pos` is matched by value against the sim's farmer / hand positions
    after the deep copy, so the caller may safely pass the original player's
    position list — `move_unit`'s in-place mutation lands on the sim's own
    list, never the original's.
    """
    sim = player.model_copy(deep=True)
    sim.step += 1

    if action.type == "PASS":
        return sim
    
    if action.type in _MARKET_TYPES:
        # `Market.apply` lives on the Market controller, but Player views
        # reconstructed from a JSON dump (e.g. inside `Environment.step`)
        # carry a plain `MarketState`. Re-wrap so the dispatch method exists.
        if not isinstance(sim.market, Market):
            sim.market = Market.model_validate(sim.market.model_dump())
        sim.market.apply(sim, action)
        return sim
    
    p = sim.player
    # Same re-wrap for the active farm: `Farm.apply` is a controller method,
    # not present on a plain `FarmState` carried by a reconstructed Player.
    if not isinstance(sim.farms[p], Farm):
        sim.farms[p] = Farm.model_validate(sim.farms[p].model_dump())
    farm = sim.farms[p]
    pos, idx = _resolve_slot(sim, unit_pos, inv_index)
    farm.apply(sim, pos, action, idx)
    
    return sim


def _resolve_slot(sim: RealityState, unit_pos, inv_index: int):
    """Return (position_list, inv_index) on the sim matching `unit_pos`.

    `move_unit` mutates `unit_pos` in place, so we must hand it the sim's
    own position list — not the caller's reference to the original's list.
    If `unit_pos` is None, defaults to the farmer slot. Otherwise matches
    by value against the farmer's position first, then each hired hand's.
    Falls back to a fresh list copy if no match (caller-supplied position
    not currently occupied by any unit on the sim).
    """
    farm = sim.farms[sim.player]
    if unit_pos is None or list(unit_pos) == list(farm.farmer):
        return farm.farmer, 0
    for k, hand_pos in enumerate(farm.hands):
        if list(unit_pos) == list(hand_pos):
            return hand_pos, k + 1
    return list(unit_pos), inv_index


def evaluate_immediate_delta(action: ActionState, player: RealityState, unit_pos=None, inv_index: int = 0) -> ResourceState:
    """Per-category resource delta from applying `action` to `player`.

    Computes `available_resources` before and after applying `action` to a
    deep copy of `player`, and returns the per-field difference as a
    `ResourceState`. A positive field means the action gained that resource;
    a negative field means it consumed some. No `resource_needs` weighting
    here — that happens in `score_action`.
    """
    before = available_resources(player)
    sim = apply_action(action, player, unit_pos=unit_pos, inv_index=inv_index)
    after = available_resources(sim)
    return ResourceState(**{
        f: getattr(after, f) - getattr(before, f)
        for f in ResourceState.model_fields
    })


def evaluate_pipeline(action: ActionState, player: RealityState, unit_pos=None, inv_index: int = 0) -> ResourceState:
    """Per-category projected (future) resource delta from `action`.

    Stub — to be reimplemented from scratch. Will capture the deferred
    consequences of an action (e.g. PLANT's future harvest sale) that are
    not reflected in the immediate state delta from `evaluate_immediate_delta`.
    """
    ...


def score_action(action: ActionState, player: RealityState, unit_pos=None, inv_index: int = 0) -> ScoredActionState:
    """Combine the direct / projection / risk evaluations into a final score.

    `direct_score` weights the per-category immediate resource delta from
    `evaluate_immediate_delta` by `resource_needs` and sums it into a scalar.
    `projected_score` does the same for the future delta from
    `evaluate_future_delta`, then scales by `FUTURE_DISCOUNT_RATE`.
    `evaluate_immediate_delta_risk` is still a stub — its contribution defaults to 0.
    `score` is the total of the three sub-scores.
    """

    delta = evaluate_immediate_delta(action, player, unit_pos=unit_pos, inv_index=inv_index)
    direct_score = sum(
        getattr(delta, f)
        for f in ResourceState.model_fields
    )

    projected_score = 0.0
    risk_score = 0.0
    score = direct_score + projected_score + risk_score
    return ScoredActionState(
        action=action,
        score=score,
        direct_score=direct_score,
        projected_score=projected_score,
        risk_score=risk_score,
    )


def score_valid_actions(valid_steps: ValidStepsState, player: RealityState) -> ScoredValidStepsState:
    """Score every action in a ValidStepsState.

    Farmer actions are scored at the farmer's slot; hired-hand actions are
    scored at each hand's position with `inv_index=k+1` so position-based
    farm actions (MOVE, PLANT, …) evaluate against the correct tile. Market
    actions are player-scoped — position is ignored.
    """
    farm = player.farms[player.player]
    farmer = [score_action(a, player) for a in valid_steps.farmer]
    hands = [
        [score_action(a, player, unit_pos=farm.hands[k], inv_index=k + 1)
         for a in hand_actions]
        for k, hand_actions in enumerate(valid_steps.hands)
    ]
    market = [score_action(a, player) for a in valid_steps.market]
    return ScoredValidStepsState(farmer=farmer, hands=hands, market=market)
