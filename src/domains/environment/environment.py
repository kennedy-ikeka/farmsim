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
import logging
from typing import ClassVar

from pydantic import Field

from src.domains.environment.town import Town
from src.domains.farm.controller import Farm
from src.domains.market.controller import Market
from src.models.game import RealityState, SharedRealityState
from src.models.player import PlayerConfig
from src.models.market import MarketInventory, MarketPrices
from src.models.player import PrivateState, SeedsState, ShedState
from src.domains.player.player import Player
from src.models.action import PassActionState
from src.models.environment import EnvironmentState, StepResultState, SimulationResultState
from src.domains.environment.clock import Clock
from src.utils.logger import get_logger

SHED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP"]
SEED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
MARKET_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


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
    logger: ClassVar[logging.Logger] = get_logger("Environment")

    def step(self):
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
        self.logger.info("step start: step=%s day=%s players=%s", self.state.step, self.state.day, len(self.state.privates))
        state = self.state

        # 1. Farm actions — each player's farmer + hands, with state.player = p.
        #    Each player's `method` and `resource_weights` travel on
        #    `state.privates[p].config`, so the per-player Player view gets
        #    them for free via its `private` field — no separate injection.
        shared = self.state.model_dump(
            exclude={'privates', 'player'}, mode='json'
        )
        players = [
            Player(**shared, player=p, private=self.state.privates[p])
            for p in range(len(self.state.privates))
        ]

        marketActions = []
        for i, p in enumerate(players):
            farm = state.farms[i]
            state.player = i
            action = p.play()
            marketActions.append(action.market)

            self.events.append(farm.apply(state, farm.farmer, action.farmer, 0))
            for i, hand_pos in enumerate(farm.hands):
                hand_action = (
                    action.hands[i]
                    if i < len(action.hands)
                    else PassActionState(type="PASS")
                )
                self.events.append(farm.apply(state, hand_pos, hand_action, i + 1))

        # 2. Market actions — interleaved one unit at a time across players.
        self.events.extend(state.market.process_orders(state, marketActions))

        # 3. Town consumption — shops + town center drain market inventory.
        self.events.extend(state.town.consume(state, self._rng))

        # 4. Time advance + end-of-day refresh on day rollover.
        self.done = self.clock.advance_time(state, self._rng) or self.done

        self.logger.info("step end: step=%s day=%s done=%s events=%s", state.step, state.day, self.done, len(self.events))
        return state

    def step_result(self) -> StepResultState:
        """Build a `StepResultState` with per-player rewards (current bank balance)."""
        return StepResultState(
            state=self.state,
            reward={p: self.state.farms[p].money for p in range(len(self.state.farms))},
            done=self.done,
        )

    def build(self, rows=10, cols=10, money=3000, farmer=(5, 5), hands=None, tiles=None, seeds=None, day=0, step=0, players=2, player_configs:list[PlayerConfig]=[]):
        shed = ShedState(**{k: 0 for k in SHED_FIELDS})
        seeds = SeedsState(**{k: 0 for k in SEED_FIELDS})

        inv = MarketInventory(**{k: 0 for k in MARKET_FIELDS})
        prices = MarketPrices(**{k: 1 for k in MARKET_FIELDS})
        market = Market(inventory=inv, prices=prices)

        if tiles is None:
            tiles = [[None] * cols for _ in range(rows)]

        build_farm = lambda: Farm(
            money=money,
            tiles=[[None if cell is None else cell for cell in row]
                   for row in tiles],
            farmer=list(farmer),
            hands=hands if hands is not None else [],
            unlocked_quadrants=["NW"],
            hires_today=0,
        )

        farms = [build_farm() for _ in range(players)]
        configs = (
            list(player_configs) if player_configs
            else [PlayerConfig() for _ in range(players)]
        )
        privates = [
            PrivateState(shed=shed, seeds=seeds, inventories=[], config=configs[p])
            for p in range(players)
        ]

        self.state = SharedRealityState(
            remainingOverageTime=60,
            step=step,
            day=day,
            hour=step % 24,
            farms=farms,
            privates=privates,
            market=market,
            town=Town(unlocked_shops=[]),
        )
        self.logger.info("build: players=%s money=%s farmer=%s rows=%s cols=%s", players, money, farmer, rows, cols)

    def simulate(self, steps: int, player_configs:list[PlayerConfig]=[]) -> SimulationResultState:
        """Run `steps` turns, each player playing per-turn, then step the world.

        `player_configs` (optional) overrides the per-player configuration
        (`method` + `resource_weights`) before running — each `PlayerConfig`
        is written onto the matching player's `private.config`. Length must
        match the number of players.

        Returns a `SimulationResultState` with each player's final bank balance
        and the winning player id (highest balance, `None` on a tie).
        """
        if player_configs:
            for p, cfg in enumerate(player_configs):
                self.state.privates[p].config = cfg

        self.logger.info("simulate start: steps=%s players=%s", steps, len(self.state.privates))
        for _ in range(steps):
            if self.done:
                self.logger.info("simulate: episode done, stopping early at step=%s", self.state.step)
                break
            self.step()

        balances = {p: self.state.farms[p].money for p in range(len(self.state.farms))}
        winner = None
        if balances:
            top = max(balances.values())
            leaders = [p for p, m in balances.items() if m == top]
            winner = leaders[0] if len(leaders) == 1 else None
        self.logger.info("simulate end: balances=%s winner=%s done=%s", balances, winner, self.done)
        return SimulationResultState(balances=balances, winner=winner, done=self.done)