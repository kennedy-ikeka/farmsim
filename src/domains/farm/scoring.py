"""Farm-side resource / future-value dispatch.

Registries mapping farm action types to the per-action `resource_usage` /
`resource_gain` / `future_gain` / `future_usage` functions defined in the
farm action modules. `player/scoring.py` calls the four dispatch functions
here via the unified `action_resource_usage` / `action_future_gain` / etc.
wrappers.

`available_resources` is also defined here — it's a player-level aggregation
over farm tiles + private shed / seeds / inventories, not a per-action
calculation, but it's farm-scoped resource accounting so it lives in the farm
domain.
"""

from src.models.action import ActionState
from src.models.game import RealityState
from src.models.resource import ResourceState

from .plant import (plant_resource_usage as plant_usage,
                    plant_future_gain as plant_fg, plant_future_usage as plant_fu)
from .water import water_future_gain as water_fg, water_future_usage as water_fu
from .fertilize import (fertilize_resource_usage as fertilize_usage,
                        fertilize_future_gain as fertilize_fg,
                        fertilize_future_usage as fertilize_fu)
from .harvest import harvest_resource_gain as harvest_gain
from .collect_fertilizer import collect_fertilizer_resource_gain as collect_fertilizer_gain
from .build_structure import (build_structure_resource_usage as build_usage,
                              build_structure_resource_gain as build_gain,
                              build_structure_future_gain as build_fg,
                              build_structure_future_usage as build_fu)
from .feed import (feed_resource_usage as feed_usage,
                   feed_future_gain as feed_fg, feed_future_usage as feed_fu)
from .care import care_future_gain as care_fg, care_future_usage as care_fu
from .dig import dig_resource_gain as dig_gain
from .place import (place_resource_gain as place_gain,
                    place_future_gain as place_fg, place_future_usage as place_fu)

_USAGE = {
    "PLANT": plant_usage,
    "FERTILIZE": fertilize_usage,
    "FEED": feed_usage,
    "BUILD_COOP": build_usage,
    "BUILD_PASTURE": build_usage,
}
_GAIN = {
    "HARVEST": harvest_gain,
    "COLLECT_FERTILIZER": collect_fertilizer_gain,
    "DIG": dig_gain,
    "PLACE": place_gain,
    "BUILD_COOP": build_gain,
    "BUILD_PASTURE": build_gain,
}
_FGAIN = {
    "PLANT": plant_fg,
    "WATER": water_fg,
    "FERTILIZE": fertilize_fg,
    "BUILD_COOP": build_fg,
    "BUILD_PASTURE": build_fg,
    "PLACE": place_fg,
    "FEED": feed_fg,
    "CARE": care_fg,
}
_FUSAGE = {
    "PLANT": plant_fu,
    "WATER": water_fu,
    "FERTILIZE": fertilize_fu,
    "BUILD_COOP": build_fu,
    "BUILD_PASTURE": build_fu,
    "PLACE": place_fu,
    "FEED": feed_fu,
    "CARE": care_fu,
}

_DEFAULT_USAGE = ResourceState(STEP=1.0)
_EMPTY = ResourceState()


def farm_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    fn = _USAGE.get(action.type)
    return fn(action, player) if fn else _DEFAULT_USAGE


def farm_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    fn = _GAIN.get(action.type)
    return fn(action, player) if fn else _EMPTY


def farm_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    fn = _FGAIN.get(action.type)
    return fn(action, player) if fn else _EMPTY


def farm_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    fn = _FUSAGE.get(action.type)
    return fn(action, player) if fn else _EMPTY

