"""Environment domain — entrance / entry point.

The `Environment` class is the top-level controller (entrance). Its `step()`
method orchestrates a single step: the farmer's action first, then each hired
hand's action in order, then up to `MAX_MARKET_ORDERS_PER_TURN` market actions.
Farm action dispatch is delegated to the `Farm` controller (living at
`state.farms[player]`) and market action dispatch to the `Market` controller
(living at `state.market`). Each `apply()` returns an `EventState` that is
appended to `self.events`.
"""
from src.models.action import PassActionState
from src.models.environment import EnvironmentState, StepState

MAX_MARKET_ORDERS_PER_TURN = 10


class Environment(EnvironmentState):
    """Controller (entrance) for the environment domain.

    The dispatch order for a single step is: farmer -> hands -> market (capped
    at `MAX_MARKET_ORDERS_PER_TURN`, extras dropped). Farm and market dispatch
    are delegated to their respective domain controllers, which return an
    `EventState` per applied action that is appended to `self.events`.
    """

    def step(self, payload: StepState):
        """Apply a set of actions for a single step to `state`, in place.

        The farmer action is applied first, then each hand action in order,
        then up to `MAX_MARKET_ORDERS_PER_TURN` market actions in order. Extra
        market orders are dropped. Returns the same (mutated) state.

        The player's farm (`state.farms[player]`) and the market
        (`state.market`) are `Farm` / `Market` controllers (IS-A `FarmState` /
        `MarketState`), so dispatch mutates the live state in place — no copy,
        no write-back. Each `apply()` returns an `EventState` (carrying the
        `intended` action parameters and the `occurred` outcome) which is
        appended to `self.events`.
        """
        state = self.state
        farm = state.farms[state.player]

        self.events.append(farm.apply(state, farm.farmer, payload.farmer, 0))

        # Pair each hand's declared action with its current position. A
        # missing action (fewer actions than hands) is treated as PASS.
        # The farmer's inventory is index 0; hand i's is index i+1.
        for i, hand_pos in enumerate(farm.hands):
            hand_action = (
                payload.hands[i]
                if i < len(payload.hands)
                else PassActionState(type="PASS")
            )
            self.events.append(farm.apply(state, hand_pos, hand_action, i + 1))

        for market_action in payload.market[:MAX_MARKET_ORDERS_PER_TURN]:
            self.events.append(state.market.apply(state, market_action))

        return state

    def step_result():
        ...