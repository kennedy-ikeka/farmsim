"""Market domain — entrance / entry point.

The `Market` class is the controller (entrance) for market actions: money,
market, shed, and animal-purchase operations performed in the market phase of
each step. Each action's implementation lives in its own module under
`src.domains.market`.

`Market` inherits `MarketState`, so a Market controller IS-A market state — the
controller's own `inventory` and `prices` are the live state mutated by the
actions (which read/write `state.market`). The GameState is passed to `apply()`
per call for the broader context (`state.privates[player]`, `state.farms[player]`).

`Market.process_orders(state, payload)` interleaves both players' market orders
one unit at a time, round-robin across players (per README "Turn Processing
Order" §3 and "Market Mechanics"). Per-unit processing lives in the
`*_one.py` modules; order-event accumulation in `order_event.py`.
"""
from src.models.action import MarketActionState
from src.models.event import EventState
from src.models.game import GameState
from src.models.market import MarketState

from src.domains.market.buy_animal import buy_animal
from src.domains.market.buy_animal_one import buy_animal_one
from src.domains.market.buy_land import buy_land
from src.domains.market.buy_land_one import buy_land_one
from src.domains.market.buy_product import buy_product
from src.domains.market.buy_product_one import buy_product_one
from src.domains.market.buy_seed import buy_seed
from src.domains.market.buy_seed_one import buy_seed_one
from src.domains.market.hire import hire
from src.domains.market.hire_one import hire_one
from src.domains.market.order_event import accumulate, build_event, init_occurred
from src.domains.market.sell import sell
from src.domains.market.sell_one import sell_one
from src.utils.config import MAX_MARKET_ORDERS_PER_TURN


# Single-shot action types (no count — one attempt, then the order is done).
_SINGLE_SHOT = {"HIRE", "BUY_LAND"}


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

    def process_orders(self, state: GameState, payload: list[MarketActionState]) -> list[EventState]:
        """Interleave both players' market orders one unit at a time.

        Returns one `EventState` per submitted order (capped at
        `MAX_MARKET_ORDERS_PER_TURN` per player), in completion order.

        Per the README, orders are processed concurrently across players, one
        unit at a time: in each round, one unit is taken from each player's
        front order at the current price, then the market inventory updates and
        the next round proceeds. An order is stopped when the player runs out
        of money or the market runs out of stock. Price is fixed within a turn
        until a future price-function pass, so the only material cross-player
        effect today is fair splitting of shared market inventory (BUY_PRODUCT)
        and per-unit affordability rechecks.

        One `EventState` is emitted per order, with `intended` = the requested
        action parameters and `occurred` = the accumulated outcome across all
        units of that order (matching the per-action `occurred` shapes from the
        action modules).
        """
        queues: list[list[list]] = []
        for p, market in enumerate(payload):
            if p >= len(state.farms):
                break
            q = []
            for i, action in enumerate(market[:MAX_MARKET_ORDERS_PER_TURN]):
                remaining = 1 if action.type in _SINGLE_SHOT else getattr(action, "count", 1)
                q.append([action, remaining, i])
            queues.append(q)

        events: list[EventState] = []
        in_flight: dict[tuple[int, int], dict] = {}
        for p, q in enumerate(queues):
            for action, _, i in q:
                in_flight[(p, i)] = init_occurred(action)

        while any(queues):
            progressed = False
            for p in range(len(queues)):
                q = queues[p]
                if not q:
                    continue
                action, remaining, order_idx = q[0]
                state.player = p
                ok, unit_occ = self._process_one_unit(state, p, action)
                accumulate(in_flight[(p, order_idx)], unit_occ)
                if action.type in _SINGLE_SHOT:
                    events.append(build_event(state, action, in_flight.pop((p, order_idx))))
                    q.pop(0)
                    progressed = True
                elif ok:
                    remaining -= 1
                    if remaining <= 0:
                        events.append(build_event(state, action, in_flight.pop((p, order_idx))))
                        q.pop(0)
                    else:
                        q[0][1] = remaining
                    progressed = True
                else:
                    events.append(build_event(state, action, in_flight.pop((p, order_idx))))
                    q.pop(0)
                    progressed = True
            if not progressed:
                break

        return events

    @staticmethod
    def _process_one_unit(state, p, action) -> tuple[bool, dict]:
        """Process one unit of `action` for player `p`. Returns (success, unit_occurred)."""
        farm = state.farms[p]
        priv = state.privates[p]
        market = state.market
        match action.type:
            case "SELL":
                return sell_one(farm, priv, market, action)
            case "BUY_SEED":
                return buy_seed_one(farm, priv, action)
            case "BUY_PRODUCT":
                return buy_product_one(farm, priv, market, action)
            case "BUY_ANIMAL":
                return buy_animal_one(farm, priv, action)
            case "HIRE":
                return hire_one(farm, action)
            case "BUY_LAND":
                return buy_land_one(farm, action)
            case _:
                raise ValueError(f"Unsupported market action: {action.type}")