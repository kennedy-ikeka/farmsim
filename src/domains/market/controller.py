"""Market domain — entrance / entry point.

The `Market` class is the controller (entrance) for market actions: money,
market, shed, and animal-purchase operations performed in the market phase of
each step. Each action's implementation lives in its own module under
`src.domains.market`.

`Market` inherits `MarketState`, so a Market controller IS-A market state — the
controller's own `inventory` and `prices` are the live state mutated by the
actions (which read/write `state.market`). The GameState is passed to `apply()`
per call for the broader context (`state.private`, `state.farms[player]`).
"""
from src.models.action import MarketActionState
from src.models.event import EventState
from src.models.game import GameState
from src.models.market import MarketState

from src.domains.market.buy_animal import buy_animal
from src.domains.market.buy_land import buy_land
from src.domains.market.buy_product import buy_product
from src.domains.market.buy_seed import buy_seed
from src.domains.market.hire import hire
from src.domains.market.sell import sell


class Market(MarketState):
    """Controller (entrance) for the market domain. IS-A `MarketState`.

    Constructed from the market data and placed at `state.market` so the
    controller IS the live market the action modules mutate (they read/write
    `state.market.inventory` / `state.market.prices`, which is `self`).
    """

    def apply(self, state: GameState, action: MarketActionState) -> EventState:
        """Dispatch a single market action to its implementation module.

        Returns an `EventState` carrying the `intended` action parameters and
        the `occurred` outcome reported by the action implementation.
        """
        match action.type:
            case "SELL":
                occurred = sell(state, action)
            case "BUY_SEED":
                occurred = buy_seed(state, action)
            case "BUY_PRODUCT":
                occurred = buy_product(state, action)
            case "BUY_ANIMAL":
                occurred = buy_animal(state, action)
            case "HIRE":
                occurred = hire(state, action)
            case "BUY_LAND":
                occurred = buy_land(state, action)
            case _:
                raise ValueError(f"Unsupported market action: {action.type}")
        return EventState(
            step=state.step,
            day=state.day,
            hour=state.hour,
            player=state.player,
            type=action.type,
            intended=action.model_dump(exclude={"type"}),
            occurred=occurred,
        )