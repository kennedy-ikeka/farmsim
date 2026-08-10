from pydantic import BaseModel, Field


class ShedState(BaseModel):
    """Items and livestock currently stored in the farm's shed."""

    WHEAT: int = Field(description="Quantity of wheat stored in the shed.")
    CARROT: int = Field(description="Quantity of carrots stored in the shed.")
    TOMATO: int = Field(description="Quantity of tomatoes stored in the shed.")
    STRAWBERRY: int = Field(description="Quantity of strawberries stored in the shed.")
    MELON: int = Field(description="Quantity of melons stored in the shed.")
    EGG: int = Field(description="Quantity of eggs stored in the shed.")
    MILK: int = Field(description="Quantity of milk stored in the shed.")
    WOOL: int = Field(description="Quantity of wool stored in the shed.")
    FERTILIZER: int = Field(description="Quantity of fertilizer stored in the shed.")
    GOOSE: int = Field(description="Number of geese owned by the farm.")
    COW: int = Field(description="Number of cows owned by the farm.")
    SHEEP: int = Field(description="Number of sheep owned by the farm.")


class SeedsState(BaseModel):
    """Seeds currently available to the farmer."""

    WHEAT: int = Field(description="Number of wheat seeds available.")
    CARROT: int = Field(description="Number of carrot seeds available.")
    TOMATO: int = Field(description="Number of tomato seeds available.")
    STRAWBERRY: int = Field(description="Number of strawberry seeds available.")
    MELON: int = Field(description="Number of melon seeds available.")


class PrivateState(BaseModel):
    """Player-specific information that is not part of the public market state."""

    shed: ShedState = Field(
        description="Contents of the player's farm shed."
    )

    seeds: SeedsState = Field(
        description="Seeds currently owned by the player."
    )

    inventories: list[dict] = Field(
        description="Additional player inventories and their contents."
    )
