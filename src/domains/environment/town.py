"""Town domain — entrance / entry point.

The `Town` class is the controller for the town's passive consumption: shop
unlocks and the periodic drain of shared market inventory by both unlocked
shops and the town center. Per README "Town Buildings" and "Turn Processing
Order" §4, the town runs after player + market actions each turn and reduces
market inventory for free (no player action, no payment).

`Town` inherits `TownState`, so a Town controller IS-A town state — the
controller's own `unlocked_shops` and scheduling counters are the live state
mutated by `consume`. The GameState is passed to `consume()` per call so the
town can read `state.day` / `state.step` and drain `state.market.inventory`.

`consume()` returns a list of `EventState` records — one per tick that
materially changed something (a shop was unlocked, or inventory was drained).
Town events carry `player = -1` to flag them as environment-driven (no player
action). Consumption floors inventory at 0 (never negative). Town-center
consumption excludes fertilizer (per README) and scales its per-product amount
with the in-game day: 1 of each until day 10, 2 of each after day 10, 4 of
each after day 20. Single-product shops (Yarn Store, Pet Cafe) consume 2 units
of their one product per tick; multi-product shops consume 1 of each demanded
product.
"""
import random

from src.models.event import EventState
from src.models.game import GameState
from src.models.town import (
    ALL_SHOPS,
    SHOP_DEMAND,
    SINGLE_PRODUCT_SHOPS,
    TOWN_CENTER_PRODUCTS,
    TownState,
)

# Sentinel player id for environment-driven events (no player action).
_NO_PLAYER = -1


class Town(TownState):
    """Controller (entrance) for the town domain. IS-A `TownState`.

    Constructed from the town data and placed at `state.town` so the controller
    IS the live town the `consume` method mutates. `consume()` is called once
    per step by `Environment.step()`, between the market phase and the time
    advance; internally it ticks shop unlocks (day-based), shop consumption
    (step-based), and town-center consumption (step-based) on their respective
    intervals. Returns one `EventState` per tick that materially changed state.
    """

    def consume(self, state: GameState, rng: random.Random) -> list[EventState]:
        """Run one turn of town processing against `state`'s market inventory.

        Order: shop unlock check → shop consumption tick → town-center
        consumption tick. Each tick is gated by its interval. Returns a list
        of `EventState` records (player = -1), one per tick that materially
        changed something; empty if no tick fired or all ticks were no-ops.
        """
        events: list[EventState] = []
        events.extend(self._maybe_unlock_shop(state, rng))
        events.extend(self._maybe_shops_consume(state))
        events.extend(self._maybe_center_consume(state))
        return events

    # ------------------------------------------------------------------
    # Shop unlocks — every `town_shop_unlock_interval` days.
    # ------------------------------------------------------------------

    def _maybe_unlock_shop(self, state: GameState, rng: random.Random) -> list[EventState]:
        if state.day - self.last_shop_unlock_day < self.town_shop_unlock_interval:
            return []
        remaining = [s for s in ALL_SHOPS if s not in self.unlocked_shops]
        unlocked = None
        if remaining:
            unlocked = rng.choice(remaining)
            self.unlocked_shops.append(unlocked)
        # Always advance the unlock day-marker, even if every shop is already
        # unlocked, so the check doesn't fire every step once saturated.
        self.last_shop_unlock_day = state.day
        if unlocked is None:
            return []  # saturated — no material change, no event
        return [EventState(
            step=state.step, day=state.day, hour=state.hour,
            player=_NO_PLAYER, type="SHOP_UNLOCK",
            intended={},
            occurred={"shop": unlocked, "unlocked_shops": list(self.unlocked_shops)},
        )]

    # ------------------------------------------------------------------
    # Shop consumption — every `town_shop_sell_interval` turns.
    # ------------------------------------------------------------------

    def _maybe_shops_consume(self, state: GameState) -> list[EventState]:
        if state.step - self.last_shop_consume_step < self.town_shop_sell_interval:
            return []
        self.last_shop_consume_step = state.step
        if not self.unlocked_shops:
            return []  # tick fired but nothing to consume — no event
        inventory = state.market.inventory
        consumed: dict[str, int] = {}
        for shop in self.unlocked_shops:
            multiplier = 2 if shop in SINGLE_PRODUCT_SHOPS else 1
            for product in SHOP_DEMAND[shop]:
                current = getattr(inventory, product, 0)
                drained = min(current, multiplier)
                if drained > 0:
                    setattr(inventory, product, current - drained)
                    consumed[product] = consumed.get(product, 0) + drained
        if not consumed:
            return []  # nothing was actually drained (all at 0) — no event
        return [EventState(
            step=state.step, day=state.day, hour=state.hour,
            player=_NO_PLAYER, type="SHOP_CONSUME",
            intended={"shops": list(self.unlocked_shops)},
            occurred={"consumed": consumed},
        )]

    # ------------------------------------------------------------------
    # Town center — every `town_center_sell_interval` turns; amount scales
    # with day (1 until day 10, 2 until day 20, 4 thereafter). Fertilizer
    # is excluded.
    # ------------------------------------------------------------------

    def _maybe_center_consume(self, state: GameState) -> list[EventState]:
        if state.step - self.last_center_consume_step < self.town_center_sell_interval:
            return []
        self.last_center_consume_step = state.step
        amount = self._center_amount(state.day)
        inventory = state.market.inventory
        consumed: dict[str, int] = {}
        for product in TOWN_CENTER_PRODUCTS:
            current = getattr(inventory, product, 0)
            drained = min(current, amount)
            if drained > 0:
                setattr(inventory, product, current - drained)
                consumed[product] = drained
        if not consumed:
            return []  # all at 0 — nothing drained — no event
        return [EventState(
            step=state.step, day=state.day, hour=state.hour,
            player=_NO_PLAYER, type="CENTER_CONSUME",
            intended={"day": state.day, "amount_per_product": amount},
            occurred={"consumed": consumed},
        )]

    @staticmethod
    def _center_amount(day: int) -> int:
        """Per-product consumption amount for the town center on a given day."""
        if day > 20:
            return 4
        if day > 10:
            return 2
        return 1