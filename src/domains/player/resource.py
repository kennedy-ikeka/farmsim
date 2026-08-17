
from typing import get_args

from src.models.action import MARKET_ACTIONS, ActionState
from src.models.farm import AnimalState, PlantState
from src.models.objects import ANIMALS, CROPS, SELLABLE_PRODUCTS
from src.models.game import RealityState
from src.models.resource import ResourceState
from src.models.farm import PlantState, AnimalState
from src.utils.config import EPISODE_STEPS
from src.models.crops import CROP_CONFIG
from src.models.animals import ANIMAL_CONFIG
from src.domains.farm.scoring import (
    farm_resource_usage,
    farm_resource_gain,
    farm_future_gain,
    farm_future_usage,
)
from src.domains.market.scoring import (
    market_resource_usage,
    market_resource_gain,
    market_future_gain,
    market_future_usage,
)

_MARKET_TYPES = set(get_args(MARKET_ACTIONS))
_RESOURCE_FIELDS = tuple(ResourceState.model_fields)


def action_resource_usage(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_resource_usage(action, player)
    return farm_resource_usage(action, player)


def action_resource_gain(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_resource_gain(action, player)
    return farm_resource_gain(action, player)


def action_future_gain(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_future_gain(action, player)
    return farm_future_gain(action, player)


def action_future_usage(action: ActionState, player: RealityState) -> ResourceState:
    if action.type in _MARKET_TYPES:
        return market_future_usage(action, player)
    return farm_future_usage(action, player)


def available_resources(player: RealityState) -> ResourceState:
    """Current amount owned of each resource."""
    farm = player.farms[player.player]
    private = player.private

    empty_tiles = sum(1 for row in farm.tiles for tile in row if tile is None)

    # SEED and ANIMAL availability is valued in economic terms (count * unit
    # cost), so a MELON seed (80) counts more than a WHEAT seed (10) and a
    # COW (400) counts more than a GOOSE (300).
    crops = get_args(CROPS)
    animals = get_args(ANIMALS)

    seed_value = sum(
        getattr(private.seeds, c) * CROP_CONFIG[c].seed_cost
        for c in crops
    )

    animal_value = sum(
        getattr(private.shed, a) * ANIMAL_CONFIG[a].cost
        for a in animals
    )
    for inv in private.inventories:
        animal_value += sum(
            getattr(inv, a) * ANIMAL_CONFIG[a].cost for a in animals
        )
    for row in farm.tiles:
        for tile in row:
            if isinstance(tile, AnimalState) and tile.animal is not None:
                animal_value += ANIMAL_CONFIG[tile.animal].cost

    # PRODUCE = raw unit count of sellable products currently held in the shed.
    produce_units = sum(
        getattr(private.shed, p, 0) for p in get_args(SELLABLE_PRODUCTS)
    )

    return ResourceState(
        MONEY=float(farm.money),
        STEP=float(EPISODE_STEPS - player.step),
        SEED=float(seed_value),
        LAND=float(empty_tiles),
        ANIMAL=float(animal_value),
        HAND=float(len(farm.hands)),
        PRODUCE=float(produce_units),
    )


def generate_resource_needs(player: RealityState) -> ResourceState:
    """Incrementally adjust resource needs based on the current pipeline state.

    Reads the player's existing `resource_needs` and nudges each field UP
    (toward 1.0) when its pipeline bottleneck is active, or DOWN (toward
    0.0) when the bottleneck has resolved, by `weight_learning_rate` per
    call. Needs therefore persist and drift across plays rather than being
    recomputed from scratch — a bottleneck that just opened ramps up over a
    few plays, and one that just closed ramps down. Clamped to [0, 1].

    Pipeline bottleneck conditions (active = nudge up, inactive = nudge down):

      SEED    — empty land but no seeds to plant.
      LAND    — seeds (or shed animals) but no empty tile to use.
      ANIMAL  — built structures but no animals to place.
      PRODUCE — have the means to make sellable goods but the shed is empty.
      MONEY   — shed has sellable produce to sell.
      HAND    — tending workload exceeds labor capacity.
      STEP    — always active (action fuel); ramps to and stays at 1.0.
    """
    needs = player.private.config.resource_needs.model_copy(deep=True)
    lr = player.private.config.weight_learning_rate

    farm = player.farms[player.player]
    shed = player.private.shed
    seeds = player.private.seeds

    empty_land = 0
    planted_crops = 0
    empty_structures = 0
    placed_animals = 0
    for row in farm.tiles:
        for tile in row:
            if tile is None:
                empty_land += 1
            elif isinstance(tile, PlantState):
                planted_crops += 1
            elif isinstance(tile, AnimalState):
                if tile.animal is None:
                    empty_structures += 1
                else:
                    placed_animals += 1

    crops = get_args(CROPS)
    animals = get_args(ANIMALS)
    sellable = get_args(SELLABLE_PRODUCTS)

    seed_count = sum(getattr(seeds, c) for c in crops)
    shed_animals = sum(getattr(shed, a) for a in animals)
    shed_produce = sum(getattr(shed, p, 0) for p in sellable)

    has_means = (
        seed_count > 0 or shed_animals > 0 or planted_crops > 0
        or placed_animals > 0 or empty_structures > 0
    )
    workload = planted_crops + placed_animals

    def adjust(field: str, active: bool) -> None:
        cur = getattr(needs, field)
        setattr(needs, field, min(1.0, cur + lr) if active else max(0.0, cur))

    # STEP — action fuel; always active so it ramps to and stays at 1.0.
    adjust("STEP", True)
    # MONEY — sell the produce already in the shed.
    adjust("MONEY", shed_produce > 0)
    # PRODUCE — have the means to make sellable goods but none yet in the shed.
    adjust("PRODUCE", has_means and shed_produce == 0)
    # SEED — empty land to plant but no seeds.
    adjust("SEED", empty_land > 0 and seed_count == 0)
    # LAND — seeds or shed animals to deploy but no empty tile to use.
    adjust("LAND", (seed_count > 0 or shed_animals > 0) and empty_land == 0)
    # ANIMAL — built structures waiting for animals.
    adjust("ANIMAL", empty_structures > 0 and shed_animals == 0)
    # HAND — tending workload exceeds the farmer + hired hands.
    adjust("HAND", workload > 1 + len(farm.hands))

    return needs