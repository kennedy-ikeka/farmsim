from typing import get_args

from src.domains.farm.move import get_valid_move_actions_for
from src.domains.farm.plant import get_valid_plant_actions_for
from src.domains.farm.water import get_valid_water_actions_for
from src.domains.farm.harvest import get_valid_harvest_actions_for
from src.domains.farm.fertilize import get_valid_fertilize_actions_for
from src.domains.farm.dig import get_valid_dig_actions_for
from src.domains.farm.build_structure import get_valid_build_actions_for
from src.domains.farm.feed import get_valid_feed_actions_for
from src.domains.farm.collect_fertilizer import get_valid_collect_fertilizer_actions_for
from src.domains.farm.care import get_valid_care_actions_for
from src.domains.farm.pickup import get_valid_pickup_actions_for
from src.domains.farm.place import get_valid_place_actions_for
from src.domains.market.buy_seed import get_valid_buy_seed_actions
from src.domains.market.buy_product import get_valid_buy_product_actions
from src.domains.market.buy_animal import get_valid_buy_animal_actions
from src.domains.market.sell import get_valid_sell_actions
from src.domains.market.hire import get_valid_hire_actions
from src.domains.market.buy_land import get_valid_buy_land_actions
from src.domains.farm import Farm
from src.domains.market import Market
from src.models.action import ActionState, PassActionState
from src.models.game import RealityState
from src.models.environment import StepState
from src.models.player import ShedState, SeedsState, PrivateState
from src.models.market import MarketInventory, MarketPrices


class Player(RealityState):
    def build(self, farmer=(5, 5), hands=None, rows=10, cols=10, seeds=None,
              tiles=None, shed=None, day=0, step=0, inventories=None,
              money=0.0, market_inventory=None, market_prices=None,
              hires_today=0, unlocked_quadrants=None):
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

    def get_valid_pass_actions(self):
        return [PassActionState()]

    def get_valid_market_actions(self) -> list:
        """All valid market actions for `player`.
        
        Aggregates one of every market per-action helper; each filters to the
        actions that would mutate state when played (at least one unit would
        succeed in the interleave loop). Returns `count=1` per viable item — the
        grading layer decides how many units to actually order.
        """
        actions: list = []
        actions.extend(get_valid_buy_seed_actions(self))
        actions.extend(get_valid_buy_product_actions(self))
        actions.extend(get_valid_buy_animal_actions(self))
        actions.extend(get_valid_sell_actions(self))
        actions.extend(get_valid_hire_actions(self))
        actions.extend(get_valid_buy_land_actions(self))
        return actions

    def get_valid_farm_actions_for(player: RealityState, unit_pos, inv_index: int) -> list:
        """All valid farm actions for a single unit (farmer or hired hand) at `unit_pos`.

        `inv_index` is the unit's slot in `player.private.inventories` (farmer = 0,
        hands = 1..N) — only PICKUP and PLACE use it. Aggregates one of every
        per-action helper; each helper filters to the actions that would actually
        mutate state when played.
        """
        actions: list = []
        farm = player.farms[player.player]
        actions.extend(get_valid_move_actions_for(farm, unit_pos))
        actions.extend(get_valid_plant_actions_for(player, unit_pos))
        actions.extend(get_valid_water_actions_for(farm, unit_pos))
        actions.extend(get_valid_harvest_actions_for(player, unit_pos))
        actions.extend(get_valid_fertilize_actions_for(player, unit_pos))
        actions.extend(get_valid_dig_actions_for(farm, unit_pos))
        actions.extend(get_valid_build_actions_for(farm, unit_pos))
        actions.extend(get_valid_feed_actions_for(player, unit_pos))
        actions.extend(get_valid_collect_fertilizer_actions_for(farm, unit_pos))
        actions.extend(get_valid_care_actions_for(farm, unit_pos))
        actions.extend(get_valid_pickup_actions_for(player, unit_pos, inv_index))
        actions.extend(get_valid_place_actions_for(player, unit_pos, inv_index))
        return actions

    def get_valid_actions(self) -> list[ActionState]:
        actions: list[ActionState] = list(self.get_valid_pass_actions())
        farm = self.farms[self.player]
        actions.extend(self.get_valid_farm_actions_for(farm.farmer, 0))
        for h, hand_pos in enumerate(farm.hands):
            actions.extend(self.get_valid_farm_actions_for(hand_pos, h + 1))
        return actions

    def play(self) -> StepState:
        farmActions = self.get_valid_actions()
        marketActions = self.get_valid_market_actions()

        print(farmActions, "\n", marketActions)
        return StepState()


def get_valid_farm_actions_for(player: RealityState, unit_pos, inv_index: int) -> list:
    """Module-level alias for `Player.get_valid_farm_actions_for`."""
    return Player.get_valid_farm_actions_for(player, unit_pos, inv_index)


def get_valid_market_actions(player) -> list:
    """Module-level alias for `Player.get_valid_market_actions`."""
    return Player.get_valid_market_actions(player)