"""Farm domain — entrance / entry point.

The `Farm` class is the controller (entrance) for farm actions: position-based
operations performed by the farmer and hired hands on the farm grid. Each
action's implementation lives in its own module under `src.domains.farm`.

`Farm` inherits `FarmState`, so a Farm controller IS-A farm state — the
controller's own `money`, `tiles`, `farmer`, `hands`, etc. are the live state
mutated by the actions. The GameState is passed to `apply()` per call for the
broader context (`state.private`, `state.day`, `state.step`).
"""
from src.models.action import FarmActionState
from src.models.event import EventState
from src.models.farm import AnimalState, FarmState, PlantState, WeedState
from src.models.game import GameState

from src.domains.farm.build_structure import build_structure
from src.domains.farm.care import care
from src.domains.farm.collect_fertilizer import collect_fertilizer
from src.domains.farm.dig import dig
from src.domains.farm.feed import feed
from src.domains.farm.fertilize import fertilize
from src.domains.farm.harvest import harvest
from src.domains.farm.move import move_unit
from src.domains.farm.pickup import pickup
from src.domains.farm.place import place
from src.domains.farm.plant import plant
from src.domains.farm.refresh_animal import refresh_animal
from src.domains.farm.refresh_plant import refresh_plant
from src.domains.farm.water import water


class Farm(FarmState):
    """Controller (entrance) for the farm domain. IS-A `FarmState`.

    Constructed from a farm's data and placed at `state.farms[player]` so the
    controller IS the live farm the action modules mutate. `apply()` passes
    `self` as the `farm` argument and `state` for the surrounding game context.
    """

    def apply(self, state: GameState, unit_pos, action: FarmActionState, inv_index: int) -> EventState:
        """Dispatch a single farm action to its implementation module.

        Returns an `EventState` carrying the `intended` action parameters and
        the `occurred` outcome reported by the action implementation.
        """
        match action.type:
            case "NORTH" | "SOUTH" | "EAST" | "WEST":
                occurred = move_unit(self, unit_pos, action.type)
            case "PASS":
                occurred = {}
            case "PLANT":
                occurred = plant(state, self, unit_pos, action)
            case "WATER":
                occurred = water(state, self, unit_pos, action)
            case "HARVEST":
                occurred = harvest(state, self, unit_pos, action)
            case "FERTILIZE":
                occurred = fertilize(state, self, unit_pos, action)
            case "DIG":
                occurred = dig(self, unit_pos, action)
            case "BUILD_COOP" | "BUILD_PASTURE":
                occurred = build_structure(self, unit_pos, action)
            case "FEED":
                occurred = feed(state, self, unit_pos, action)
            case "COLLECT_FERTILIZER":
                occurred = collect_fertilizer(state, self, unit_pos, action)
            case "CARE":
                occurred = care(self, unit_pos, action)
            case "PICKUP":
                occurred = pickup(state, self, unit_pos, action, inv_index)
            case "PLACE":
                occurred = place(state, self, unit_pos, action, inv_index)
            case _:
                raise ValueError(f"Unsupported farm action: {action.type}")
        return EventState(
            step=state.step,
            day=state.day,
            hour=state.hour,
            player=state.player,
            type=action.type,
            intended=action.model_dump(exclude={"type"}),
            occurred=occurred,
        )

    def refresh_tiles(self, state: GameState) -> None:
        """Run the per-tile end-of-day refresh across this farm's grid.

        Dispatches each tile in place to the appropriate per-tile refresh:
        `PlantState` tiles to `refresh_plant` (which may reassign the slot
        to a `WeedState`), `AnimalState` tiles to `refresh_animal` (which
        mutates the tile in place), and leaves `None`, `WeedState`, and
        `LOCKED` tiles untouched.
        """
        for r, row in enumerate(self.tiles):
            for c, tile in enumerate(row):
                if isinstance(tile, PlantState):
                    refresh_plant(state, self, r, c, tile)
                elif isinstance(tile, AnimalState):
                    refresh_animal(tile)
                # None, WeedState, and "LOCKED" tiles need no refresh.