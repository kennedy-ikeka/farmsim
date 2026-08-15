from typing_extensions import Literal

from pydantic import BaseModel, Field

# How a player chooses actions each turn. Lives here (not in game.py) so
# `PlayerConfig` can carry a per-player `method` without importing game.py
# (which imports PrivateState — that would be a circular import).
PLAY_METHODS = Literal["RANDOM", "BASIC", "TACTICAL"]

class ScoreWeights(BaseModel):
    COST: float = Field(1.0, description="Weight for cost in action scoring.")
    REWARD: float = Field(1.0, description="Weight for reward in action scoring.")
    FUTURE_COST: float = Field(1.0, description="Weight for future cost in action scoring.")
    FUTURE_REWARD: float = Field(1.0, description="Weight for future reward in action scoring.")
    FUTURE_DISCOUNT_RATE: float = Field(1.0, description="How much we care about the future")


class ResourceWeights(BaseModel):
    """Per-resource weights used when scoring actions.

    Each weight multiplies the `(usage / available)` term for that resource in
    the cost and reward scores. Defaults are 1.0 so every resource is valued
    equally out of the box; override individual fields to bias scoring (e.g.
    bump `STEP` to penalize turn-spending, or `MONEY` to be thriftier).
    """

    MONEY: float = Field(1.0, description="Weight for money in action scoring.")
    STEP: float = Field(1.0, description="Weight for step/turn usage in action scoring.")
    SEED: float = Field(1.0, description="Weight for seed value in action scoring.")
    LAND: float = Field(1.0, description="Weight for empty land tiles in action scoring.")
    ANIMAL: float = Field(1.0, description="Weight for animal value in action scoring.")
    HAND: float = Field(1.0, description="Weight for hired hands in action scoring.")


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
    score_weights: ScoreWeights = Field(
        default_factory=ScoreWeights,
        description="Per-score weights for this player."
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
        default_factory=list,
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
