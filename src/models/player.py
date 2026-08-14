from pydantic import BaseModel, Field


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
