"""Shared test fixture for building a minimal `Environment` instance."""
from src.domains.environment import Environment
from src.domains.farm import Farm
from src.domains.market import Market
from src.models.game import GameState
from src.models.market import MarketInventory, MarketPrices
from src.models.player import PrivateState, SeedsState, ShedState
from src.models.town import TownState

SHED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP"]
SEED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
MARKET_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def _zero_shed():
    return ShedState(**{k: 0 for k in SHED_FIELDS})


def _zero_seeds():
    return SeedsState(**{k: 0 for k in SEED_FIELDS})


def _zero_market():
    inv = MarketInventory(**{k: 0 for k in MARKET_FIELDS})
    prices = MarketPrices(**{k: 1 for k in MARKET_FIELDS})
    # Market controller (IS-A MarketState) lives at state.market so dispatch
    # mutates the live market in place.
    return Market(inventory=inv, prices=prices)


def _make_env(rows=10, cols=10, farmer=(5, 5), hands=None, tiles=None,
             seeds=None, day=0, step=0):
    """Build a minimal Environment whose `state` is a valid GameState.

    `seeds` may be a {crop: count} dict to pre-populate the seed slot. The farm
    and market slots are `Farm` / `Market` controllers (IS-A `FarmState` /
    `MarketState`) so `env.step()` dispatch mutates the live state in place.
    """
    if tiles is None:
        tiles = [[None] * cols for _ in range(rows)]

    seed_state = _zero_seeds()
    if seeds:
        for crop, count in seeds.items():
            setattr(seed_state, crop, count)

    farm = Farm(
        money=0.0,
        tiles=tiles,
        farmer=list(farmer),
        hands=hands if hands is not None else [],
        unlocked_quadrants=["NW"],
        hires_today=0,
    )

    state = GameState(
        remainingOverageTime=60,
        step=step,
        day=day,
        hour=0,
        player=0,
        farms=[farm],
        private=PrivateState(shed=_zero_shed(), seeds=seed_state, inventories=[]),
        market=_zero_market(),
        town=TownState(unlocked_shops=[]),
    )
    return Environment(state=state)
