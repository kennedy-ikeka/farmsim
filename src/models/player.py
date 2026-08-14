from typing_extensions import Literal

from pydantic import BaseModel, Field

from src.models.resource_weights import ResourceWeights

# How a player chooses actions each turn. Lives here (not in game.py) so
# `PlayerConfig` can carry a per-player `method` without importing game.py
# (which imports PrivateState — that would be a circular import).
PLAY_METHODS = Literal["RANDOM", "BEST_CHOISE", "TACTICAL"]


class PlayerConfig(BaseModel):
    """Per-player configuration: play method + scoring weights.

    Nested inside each player's `PrivateState` (one config per player), so
    `Environment.step` reads `state.privates[p].config` to drive that
    player's `play()` dispatch and scoring weights. No separate parallel
    list on the shared state — the config travels with the private state.
    """

    method: PLAY_METHODS = Field(
        'RANDOM',
        description="How this player chooses actions each turn."
    )
    resource_weights: ResourceWeights = Field(
        default_factory=ResourceWeights,
        description="Per-resource scoring weights for this player."
    )


class ShedState(BaseModel):
    """Items and livestock currently stored in the farm's shed."""

    WHEAT: int = Field(0, description="Quantity of wheat stored in the shed.")
    CARROT: int = Field(0, description="Quantity of carrots stored in the shed.")
    TOMATO: int = Field(0, description="Quantity of tomatoes stored in the shed.")
    STRAWBERRY: int = Field(0, description="Quantity of strawberries stored in the shed.")
    MELON: int = Field(0, description="Quantity of melons stored in the shed.")
    EGG: int = Field(0, description="Quantity of eggs stored in the shed.")
    MILK: int = Field(0, description="Quantity of milk stored in the shed.")
    WOOL: int = Field(0, description="Quantity of wool stored in the shed.")
    FERTILIZER: int = Field(0, description="Quantity of fertilizer stored in the shed.")
    GOOSE: int = Field(0, description="Number of geese owned by the farm.")
    COW: int = Field(0, description="Number of cows owned by the farm.")
    SHEEP: int = Field(0, description="Number of sheep owned by the farm.")


class SeedsState(BaseModel):
    """Seeds currently available to the farmer."""

    WHEAT: int = Field(0, description="Number of wheat seeds available.")
    CARROT: int = Field(0, description="Number of carrot seeds available.")
    TOMATO: int = Field(0, description="Number of tomato seeds available.")
    STRAWBERRY: int = Field(0, description="Number of strawberry seeds available.")
    MELON: int = Field(0, description="Number of melon seeds available.")


class InventoryState(BaseModel):
    """Items currently carried by a single unit (farmer or hired hand).

    Mirrors `ShedState`'s 12 fields — every item that can be picked up from
    the shed or carried by a unit. Fields default to 0 and are always present
    (no key deletion); an empty inventory is the all-zero state.
    """

    WHEAT: int = Field(0, description="Quantity of wheat carried.")
    CARROT: int = Field(0, description="Quantity of carrots carried.")
    TOMATO: int = Field(0, description="Quantity of tomatoes carried.")
    STRAWBERRY: int = Field(0, description="Quantity of strawberries carried.")
    MELON: int = Field(0, description="Quantity of melons carried.")
    EGG: int = Field(0, description="Quantity of eggs carried.")
    MILK: int = Field(0, description="Quantity of milk carried.")
    WOOL: int = Field(0, description="Quantity of wool carried.")
    FERTILIZER: int = Field(0, description="Quantity of fertilizer carried.")
    GOOSE: int = Field(0, description="Number of geese carried.")
    COW: int = Field(0, description="Number of cows carried.")
    SHEEP: int = Field(0, description="Number of sheep carried.")


class PrivateState(BaseModel):
    """Player-specific information that is not part of the public market state."""

    shed: ShedState = Field(
        default_factory=ShedState,
        description="Contents of the player's farm shed."
    )

    seeds: SeedsState = Field(
        default_factory=SeedsState,
        description="Seeds currently owned by the player."
    )

    inventories: list[InventoryState] = Field(
        default=list,
        description="Per-unit inventories (farmer at index 0, then hired hands)."
    )

    config: PlayerConfig = Field(
        default_factory=PlayerConfig,
        description=(
            "Per-player configuration (play method + scoring weights). "
            "Nested here so it travels with the private state — no separate "
            "config list on the shared state."
        )
    )
