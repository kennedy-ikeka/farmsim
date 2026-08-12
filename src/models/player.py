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

    inventories: list[dict] = Field(
        default=list,
        description="Additional player inventories and their contents."
    )
