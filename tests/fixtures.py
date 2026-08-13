"""Shared test fixture for building a minimal `Environment` instance."""
from unittest.mock import patch

from src.domains.environment import Environment
from src.domains.environment.town import Town
from src.domains.farm import Farm
from src.domains.market import Market
from src.domains.player.player import Player
from src.models.environment import StepState
from src.models.game import SharedRealityState
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
             seeds=None, day=0, step=0, players=1):
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

    state = SharedRealityState(
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


def _play(env, *per_player_steps, default=None):
    """Run one `env.step()` with scripted per-player actions.

    Patches `Player.play` so player `p` returns `per_player_steps[p]`. Players
    beyond the supplied steps play `default` (an all-PASS `StepState` from
    `_step()` if not given). Replaces the old `_turn(payload)` + payload-driven
    `env.step(payload)` flow now that `Environment.step` is player-driven.

    Examples:
        _play(env, step)              # player 0 plays `step`, others pass
        _play(env, step0, step1)      # both players scripted (2-player env)
        _play(env, _step())           # equivalent to a pure pass turn
    """
    default_step = default if default is not None else _step()
    steps = list(per_player_steps)

    def _scripted_play(self):
        return steps[self.player] if self.player < len(steps) else default_step

    with patch.object(Player, "play", _scripted_play):
        env.step()


def _step(farmer=None, hands=None, market=None):
    """Convenience StepState builder (all-PASS defaults if omitted)."""
    from src.models.action import PassActionState
    return StepState(
        farmer=farmer if farmer is not None else PassActionState(type="PASS"),
        hands=hands if hands is not None else [],
        market=market if market is not None else [],
    )