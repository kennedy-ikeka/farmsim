"""Environment domain — entrance / entry point.

The `Environment` class is the top-level controller (entrance). Its `step()`
method orchestrates a full two-player turn: each player's farmer + hand farm
actions (with `state.player` set per player), then both players' market orders
interleaved one unit at a time round-robin, then the town's passive consumption
of market inventory, then time advancement with an end-of-day refresh when the
day rolls over. Farm action dispatch is delegated to the `Farm` controller
(living at `state.farms[p]`); market interleaving to `process_market_orders`;
town consumption to the `Town` controller (living at `state.town`); time +
end-of-day to the `Clock` controller.
"""

import random

from pydantic import Field

from src.models.action import PassActionState
from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.models.environment import EnvironmentState, StepResultState, TurnActions
from src.domains.environment.clock import Clock

# Re-exported for tests that import MAX_MARKET_ORDERS_PER_TURN from here.
__all__ = ["Environment", "MAX_MARKET_ORDERS_PER_TURN"]


class Environment(EnvironmentState):
    """Controller (entrance) for the environment domain.

    The dispatch order for a single step is: each player's farmer → that
    player's hands (in order) → market orders interleaved across players one
    unit at a time → town consumption (shops + town center drain market
    inventory) → time advance (with end-of-day refresh when the day rolls
    over). Farm dispatch is delegated to the `Farm` controller at
    `state.farms[p]`; market interleaving to `process_market_orders`; town
    consumption to the `Town` controller at `state.town`; time + end-of-day
    to the owned `Clock` instance.
    """

    # Override the model-typed field with the controller subtype so a bare
    # `Environment(...)` defaults to a `Clock` (with behaviour) rather than a
    # behaviourless `ClockState`. Keeps the model layer free of domain imports.
    clock: Clock = Field(default_factory=Clock)

    def step(self, payload: TurnActions):
        """Apply all players' actions for a single step to `state`, in place.

        For each player `p` (in id order), `state.player` is set to `p` and that
        player's farmer + hand farm actions are applied via `Farm.apply`.
        Market orders from all players are then interleaved one unit at a time
        round-robin via `process_market_orders`. The town then consumes market
        inventory (shop + town-center ticks, per README "Turn Processing Order"
        §4). Finally the step counter advances and, if the day rolled over, the
        `Clock.end_of_day_refresh` runs.

        Each applied action appends one `EventState` (carrying `intended` and
        `occurred`) to `self.events`. Returns the same (mutated) state.
        """
        state = self.state

        # 1. Farm actions — each player's farmer + hands, with state.player = p.
        for p, step_payload in enumerate(payload.actions):
            if p >= len(state.farms):
                break
            state.player = p
            farm = state.farms[p]
            self.events.append(farm.apply(state, farm.farmer, step_payload.farmer, 0))
            for i, hand_pos in enumerate(farm.hands):
                hand_action = (
                    step_payload.hands[i]
                    if i < len(step_payload.hands)
                    else PassActionState(type="PASS")
                )
                self.events.append(farm.apply(state, hand_pos, hand_action, i + 1))

        # 2. Market actions — interleaved one unit at a time across players.
        self.events.extend(state.market.process_orders(state, payload))

        # 3. Town consumption — shops + town center drain market inventory.
        self.events.extend(state.town.consume(state, self._rng))

        # 4. Time advance + end-of-day refresh on day rollover.
        self.done = self.clock.advance_time(state, self._rng) or self.done

        return state

    def step_result(self) -> StepResultState:
        """Build a `StepResultState` with per-player rewards (current bank balance)."""
        return StepResultState(
            state=self.state,
            reward={p: self.state.farms[p].money for p in range(len(self.state.farms))},
            done=self.done,
        )