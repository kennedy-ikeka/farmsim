import logging
import random
from typing import ClassVar

from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.domains.farm import Farm
from src.domains.market import Market
from src.models.action import PassActionState
from src.models.game import RealityState, SharedRealityState
from src.models.environment import StepState
from src.models.player import PlayerConfig, ShedState, SeedsState, PrivateState, ResourceWeights
from src.models.market import MarketInventory, MarketPrices
from src.domains.player.valid_actions import get_valid_actions
from src.domains.player.scoring import (
    score_valid_actions,
    score_action,
    update_resource_weights,
)
from src.utils.logger import get_logger


class Player(RealityState):
    logger: ClassVar[logging.Logger] = get_logger("Player")
    def build(self, farmer=(5, 5), hands=None, rows=10, cols=10, seeds=None,
              tiles=None, shed=None, day=0, step=0, inventories=None,
              money=0.0, market_inventory=None, market_prices=None,
              hires_today=0, unlocked_quadrants=None,
              method='RANDOM', resource_weights=None):
        """Build a Player view over a single-player env, pre-populating player 0.

        Mirrors `Environment.build` — assembles a one-farm / one-private state
        in place on `self`, so `get_valid_actions` sees the same farm shapes
        that `Environment.step` would present to player 0. Returns `self` for
        one-liner test construction (`player = Player().build(...)`).

        The market is constructed with all-zero inventory and all-one prices
        (matching `_make_env` / `Environment.build`), NOT the `MarketInventory` /
        `MarketPrices` model defaults (10_000 stock, real prices) — the market
        validity tests rely on the empty/flat default.
        """
        from src.domains.environment.town import Town  # lazy: avoids the
        # environment→Player→environment cycle when tests import Player first.

        shed_state = ShedState()                       # all fields default 0
        seeds_state = SeedsState()                     # all fields default 0
        if shed:
            for item, count in shed.items():
                setattr(shed_state, item, count)
        if seeds:
            for crop, count in seeds.items():
                setattr(seeds_state, crop, count)
        priv = PrivateState(
            shed=shed_state, seeds=seeds_state,
            inventories=list(inventories) if inventories else [],
            config=PlayerConfig(
                method=method,
                resource_weights=resource_weights if resource_weights is not None else ResourceWeights(),
            ),
        )

        inv = MarketInventory(**{f: 0 for f in MarketInventory.model_fields})
        prices = MarketPrices(**{f: 1 for f in MarketPrices.model_fields})
        if market_inventory:
            for item, count in market_inventory.items():
                setattr(inv, item, count)
        if market_prices:
            for item, price in market_prices.items():
                setattr(prices, item, price)
        market = Market(inventory=inv, prices=prices)

        if tiles is None:
            tiles = [[None] * cols for _ in range(rows)]
        quads = list(unlocked_quadrants) if unlocked_quadrants is not None else ["NW"]
        farm = Farm(
            money=money,
            tiles=[[None if cell is None else cell for cell in row] for row in tiles],
            farmer=list(farmer),
            hands=hands if hands is not None else [],
            unlocked_quadrants=quads,
            hires_today=hires_today,
        )

        self.remainingOverageTime = 60
        self.step = step
        self.day = day
        self.hour = step % 24
        self.player = 0
        self.farms = [farm]
        self.market = market
        self.town = Town(unlocked_shops=[])
        self.private = priv
        return self

    def random_play(self) -> StepState:
        actions = get_valid_actions(self)
        farmer = random.choice(actions.farmer) if actions.farmer else PassActionState()
        hands = [
            random.choice(acts) if acts else PassActionState()
            for acts in actions.hands
        ]
        market = random.choices(actions.market, k=MAX_MARKET_ORDERS_PER_TURN) if actions.market else []
        step = StepState(farmer=farmer, hands=hands, market=market)
        self.logger.info("random_play: player=%s farmer=%s hands=%s market=%s", self.player, farmer.type, [h.type for h in hands], [m.type for m in market])
        return step

    def basic_play(self) -> StepState:
        """Shared scoring-based selection for BASIC / TACTICAL.

        Each action is picked by scoring valid actions, then SIMULATED on a
        deep copy of the state before re-planning the next. This means:

        - After buying an animal (money drops), the next buy is re-scored
          against the reduced bank balance — unaffordable buys vanish from
          valid actions and scarcity rises on the rest.
        - After planting on a tile, the next hand sees that tile occupied.
        - Weights satiate after each pick so the resource that drove one
          action is less influential for the next.

        The simulation copy is discarded after selection; the real state is
        left clean for `Environment.step` to execute the chosen actions.
        Only the satiated weights are written back to the real player.
        """
        # --- Build a simulation copy with Farm/Market controllers ----------
        sim = self.model_copy(deep=True)
        sim.farms = [
            f if isinstance(f, Farm) else Farm(**f.model_dump())
            for f in sim.farms
        ]
        if not isinstance(sim.market, Market):
            sim.market = Market(**sim.market.model_dump())
        # SharedRealityState view over the same refs — action execution
        # functions read `state.privates[state.player]`, not `state.private`.
        # Place sim.private at index sim.player so the lookup resolves for
        # any player id (other slots are dummies — only the active player's
        # state is mutated during simulation).
        privates = [PrivateState() for _ in range(sim.player)]
        privates.append(sim.private)
        sim_shared = SharedRealityState(
            remainingOverageTime=sim.remainingOverageTime,
            step=sim.step, day=sim.day, hour=sim.hour, player=sim.player,
            farms=sim.farms, market=sim.market, town=sim.town,
            privates=privates,
        )

        # --- Farmer --------------------------------------------------------
        valid = get_valid_actions(sim)
        farmer_scored = [score_action(a, sim) for a in valid.farmer]
        best_farmer = max(farmer_scored, key=lambda s: s.score) if farmer_scored else None
        if best_farmer and best_farmer.score > 0:
            farmer = best_farmer.action
            sim.farms[sim.player].apply(
                sim_shared, sim.farms[sim.player].farmer, best_farmer.action, 0
            )
            update_resource_weights(sim, [best_farmer])
        else:
            farmer = PassActionState()

        # --- Hands (re-plan from simulated state after each pick) ----------
        hands = []
        num_hands = len(sim.farms[sim.player].hands)
        for hand_idx in range(num_hands):
            valid = get_valid_actions(sim)
            hand_actions = valid.hands[hand_idx] if hand_idx < len(valid.hands) else []
            hand_scored = [score_action(a, sim) for a in hand_actions]
            best = max(hand_scored, key=lambda s: s.score) if hand_scored else None
            if best and best.score > 0:
                hands.append(best.action)
                sim.farms[sim.player].apply(
                    sim_shared,
                    sim.farms[sim.player].hands[hand_idx],
                    best.action, hand_idx + 1,
                )
                update_resource_weights(sim, [best])
            else:
                hands.append(PassActionState())

        # --- Market (greedy: pick, simulate, re-plan, repeat) --------------
        market = []
        for _ in range(MAX_MARKET_ORDERS_PER_TURN):
            valid = get_valid_actions(sim)
            if not valid.market:
                break
            scored = [score_action(a, sim) for a in valid.market]
            best = max(scored, key=lambda s: s.score)
            if best.score <= 0:
                break
            market.append(best.action)
            sim.market.apply(sim_shared, best.action)
            update_resource_weights(sim, [best])

        # --- Persist satiated weights to the real player -------------------
        self.private.config.resource_weights = sim.private.config.resource_weights

        step = StepState(farmer=farmer, hands=hands, market=market)
        self.logger.info("%s: player=%s farmer=%s hands=%s market=%s", 'basic_play', self.player, farmer.type, [h.type for h in hands], [m.type for m in market])
        return step

    def play(self) -> StepState:
        method = self.private.config.method
        self.logger.info("play: player=%s method=%s", self.player, method)
        if method == 'RANDOM':
            return self.random_play()

        if method == 'BASIC':
            return self.basic_play()

        if method == 'TACTICAL':
            return self.tactical_play()

        self.logger.warning("play: unknown method=%s, falling back to PASS", method)
        return StepState()
