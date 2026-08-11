"""Clock controller — advances the in-game clock and runs the end-of-day refresh.

`Clock` IS-A `ClockState`: it carries the configurable knobs (turns per day,
episode length, shed capacity, weed-spawn chance) as model fields and adds the
behaviour on top. `Environment` owns a `Clock` instance and delegates time
advancement + day-rollover refresh to it.

Day refresh (per README "Turn Processing Order" §5) runs for every player: reset
daily flags, advance consecutive-miss counters (plants → weeds, animals escape
at 2), bank care bonuses, set fertilizer availability, apply plant decay, spawn
weeds, reset hires, drop hand inventories to the shed, and clear hands (they
disappear at end of day, re-hired next day). The main farmer persists across
days (keeps their inventory); only hired hands drop their inventory and leave.

The per-tile refresh logic lives in the farm domain
(`src.domains.farm.refresh_plant`, `refresh_animal`); the `Farm` controller's
`refresh_tiles(state)` method dispatches each tile to the right per-tile
refresh. `spawn_weeds` and `drop_hand_inventories` also live in the farm
domain; this controller orchestrates them per player.

Animal scheduled production *payout* (base 1 + banked bonus on scheduled days)
is deferred — only `pending_care_bonus` banking is implemented here.
"""
import random

from src.models.game import GameState
from src.models.clock import ClockState

from src.domains.farm.spawn_weeds import spawn_weeds
from src.domains.farm.drop_hand_inventories import drop_hand_inventories_to_shed


class Clock(ClockState):
    """Controller for time advancement and end-of-day refresh.

    `advance_time(state, rng)` advances the step/hour/day counters on `state`
    and runs `end_of_day_refresh` when the day rolls over; returns `True` once
    the episode has reached `episode_steps` (the `done` signal).
    """

    def advance_time(self, state: GameState, rng: random.Random) -> bool:
        """Advance step/hour/day; run end-of-day refresh when the day rolls over.

        Returns `True` when the episode has reached `episode_steps`.
        """
        prev_day = state.day
        state.step += 1
        state.hour = state.step % self.turns_per_day
        state.day = state.step // self.turns_per_day
        if state.day > prev_day:
            self.end_of_day_refresh(state, rng)
        return state.step >= self.episode_steps

    def end_of_day_refresh(self, state: GameState, rng: random.Random) -> None:
        """Run the end-of-day refresh for every player's farm and private state."""
        for p in range(len(state.farms)):
            farm = state.farms[p]
            priv = state.privates[p]
            farm.refresh_tiles(state)
            spawn_weeds(farm, self.weed_spawn_chance, rng)
            farm.hires_today = 0
            drop_hand_inventories_to_shed(farm, priv, self.shed_capacity)
            farm.hands = []

            # The farmer keeps their inventory; truncate inventories to [farmer_inv].
            if len(priv.inventories) > 1:
                priv.inventories = priv.inventories[:1]
                