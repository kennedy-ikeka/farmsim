import logging
import random
from typing import ClassVar

from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.domains.farm import Farm
from src.domains.market import Market
from src.models.action import PassActionState
from src.models.game import RealityState
from src.models.environment import StepState
from src.models.player import PlayerConfig, ShedState, SeedsState, PrivateState
from src.models.resource_weights import ResourceWeights
from src.models.market import MarketInventory, MarketPrices
from src.domains.player.valid_actions import get_valid_actions
from src.domains.player.scoring import score_valid_actions
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

    def best_play(self) -> StepState:
        """Select the highest-scoring valid action for each slot, by score alone.

        Farmer and each hand take their single highest-scored action; market
        takes the top `MAX_MARKET_ORDERS_PER_TURN` highest-scored market
        actions (no repeats — distinct actions only). Empty slots fall back
        to PASS.
        """
        scored = score_valid_actions(get_valid_actions(self), self)
        farmer = (
            max(scored.farmer, key=lambda s: s.score).action
            if scored.farmer else PassActionState()
        )
        hands = [
            max(hand, key=lambda s: s.score).action if hand else PassActionState()
            for hand in scored.hands
        ]
        top_market = sorted(scored.market, key=lambda s: s.score, reverse=True)[:MAX_MARKET_ORDERS_PER_TURN]
        market = [s.action for s in top_market]
        step = StepState(farmer=farmer, hands=hands, market=market)
        self.logger.info("best_play: player=%s farmer=%s hands=%s market=%s", self.player, farmer.type, [h.type for h in hands], [m.type for m in market])
        return step

    def tactical_play(self):
        self.logger.info("tactical_play: player=%s (no-op)", self.player)
        return StepState()

    def play(self) -> StepState:
        method = self.private.config.method
        self.logger.info("play: player=%s method=%s", self.player, method)
        if method == 'RANDOM':
            return self.random_play()

        if method == 'BEST_CHOISE':
            return self.best_play()

        if method == 'TACTICAL':
            return self.tactical_play()

        self.logger.warning("play: unknown method=%s, falling back to PASS", method)
        return StepState()
