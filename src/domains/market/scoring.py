"""Market-side resource / future-value dispatch.

Registries mapping market action types to the per-action `resource_usage` /
`resource_gain` / `future_gain` / `future_usage` functions defined in the
market action modules. `player/scoring.py` calls the four dispatch functions
here via the unified `action_resource_usage` / `action_future_gain` / etc.
wrappers.

No market action has deferred spend, so `market_future_usage` always returns
an empty `ResourceState`.
"""
from src.models.action import ActionState
from src.models.game import RealityState
from src.models.resource import ResourceState

from .sell import sell_resource_usage as sell_usage, sell_resource_gain as sell_gain
from .buy_seed import (buy_seed_resource_usage as buy_seed_usage,
                       buy_seed_resource_gain as buy_seed_gain,
                       buy_seed_future_gain as buy_seed_fg)
from .buy_product import (buy_product_resource_usage as buy_product_usage,
                          buy_product_resource_gain as buy_product_gain)
from .buy_animal import (buy_animal_resource_usage as buy_animal_usage,
                         buy_animal_resource_gain as buy_animal_gain,
                         buy_animal_future_gain as buy_animal_fg)
from .hire import hire_resource_usage as hire_usage, hire_resource_gain as hire_gain
from .buy_land import (buy_land_resource_usage as buy_land_usage,
                       buy_land_resource_gain as buy_land_gain)

_USAGE = {
    "SELL": sell_usage,
    "BUY_SEED": buy_seed_usage,
    "BUY_PRODUCT": buy_product_usage,
    "BUY_ANIMAL": buy_animal_usage,
    "HIRE": hire_usage,
    "BUY_LAND": buy_land_usage,
}
_GAIN = {
    "SELL": sell_gain,
    "BUY_SEED": buy_seed_gain,
    "BUY_ANIMAL": buy_animal_gain,
    "BUY_PRODUCT": buy_product_gain,
    "HIRE": hire_gain,
    "BUY_LAND": buy_land_gain,
}
_FGAIN = {
    "BUY_SEED": buy_seed_fg,
    "BUY_ANIMAL": buy_animal_fg,
}
# No market action has future_usage.

_DEFAULT_USAGE = ResourceState(STEP=1.0)
_EMPTY = ResourceState()


def market_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    fn = _USAGE.get(action.type)
    return fn(action, player) if fn else _DEFAULT_USAGE


def market_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    fn = _GAIN.get(action.type)
    return fn(action, player) if fn else _EMPTY


def market_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    fn = _FGAIN.get(action.type)
    return fn(action, player) if fn else _EMPTY


def market_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    return _EMPTY