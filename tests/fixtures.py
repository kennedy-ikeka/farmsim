"""Shared test fixture for building a minimal `Environment` instance."""
from src.domains.environment import Environment
from src.domains.environment.town import Town
from src.domains.farm import Farm
from src.domains.market import Market
from src.models.environment import StepState, TurnActions
from src.models.game import GameState
from src.models.market import MarketInventory, MarketPrices
from src.models.player import PrivateState, SeedsState, ShedState

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
             seeds=None, day=0, step=0, players=2):
    """Build a minimal Environment whose `state` is a valid two-player GameState.

    `seeds` may be a {crop: count} dict to pre-populate player 0's seed slot.
    The farm and market slots are `Farm` / `Market` controllers (IS-A `FarmState` /
    `MarketState`) so `env.step()` dispatch mutates the live state in place.
    """
    if tiles is None:
        tiles = [[None] * cols for _ in range(rows)]

    def _build_farm():
        return Farm(
            money=0.0,
            tiles=[[None if cell is None else cell for cell in row]
                   for row in tiles],
            farmer=list(farmer),
            hands=hands if hands is not None else [],
            unlocked_quadrants=["NW"],
            hires_today=0,
        )

    farms = [_build_farm() for _ in range(players)]
    privates = [PrivateState(shed=_zero_shed(), seeds=_zero_seeds(), inventories=[])
                for _ in range(players)]
    if seeds:
        for crop, count in seeds.items():
            setattr(privates[0].seeds, crop, count)

    state = GameState(
        remainingOverageTime=60,
        step=step,
        day=day,
        hour=step % 24,
        player=0,
        farms=farms,
        privates=privates,
        market=_zero_market(),
        town=Town(unlocked_shops=[]),
    )
    return Environment(state=state, seed=42)


def _turn(*step_states):
    """Build a `TurnActions` payload from per-player `StepState`s.

    Missing players (fewer StepStates than farms) default to an all-PASS
    `StepState` so single-player tests wrap minimally: `_turn(my_step)`.
    """
    actions = list(step_states)
    return TurnActions(actions=actions)


def _step(farmer=None, hands=None, market=None):
    """Convenience StepState builder (all-PASS defaults if omitted)."""
    from src.models.action import PassActionState
    return StepState(
        farmer=farmer if farmer is not None else PassActionState(type="PASS"),
        hands=hands if hands is not None else [],
        market=market if market is not None else [],
    )