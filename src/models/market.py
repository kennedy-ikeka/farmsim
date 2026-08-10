from pydantic import BaseModel, Field


class MarketInventory(BaseModel):
    """Quantities of goods currently available in the market."""

    WHEAT: int = Field(description="Wheat units available for purchase.")
    CARROT: int = Field(description="Carrot units available for purchase.")
    TOMATO: int = Field(description="Tomato units available for purchase.")
    STRAWBERRY: int = Field(description="Strawberry units available for purchase.")
    MELON: int = Field(description="Melon units available for purchase.")
    EGG: int = Field(description="Egg units available for purchase.")
    MILK: int = Field(description="Milk units available for purchase.")
    WOOL: int = Field(description="Wool units available for purchase.")
    FERTILIZER: int = Field(description="Fertilizer units available for purchase.")


class MarketPrices(BaseModel):
    """Current market price of each tradable item."""

    WHEAT: int = Field(description="Current market price of one unit of wheat.")
    CARROT: int = Field(description="Current market price of one unit of carrots.")
    TOMATO: int = Field(description="Current market price of one unit of tomatoes.")
    STRAWBERRY: int = Field(description="Current market price of one unit of strawberries.")
    MELON: int = Field(description="Current market price of one unit of melons.")
    EGG: int = Field(description="Current market price of one unit of eggs.")
    MILK: int = Field(description="Current market price of one unit of milk.")
    WOOL: int = Field(description="Current market price of one unit of wool.")
    FERTILIZER: int = Field(description="Current market price of one unit of fertilizer.")


class MarketState(BaseModel):
    """Current state of the game's marketplace."""

    inventory: MarketInventory = Field(
        description="Available quantities of tradable goods."
    )

    prices: MarketPrices = Field(
        description="Current prices for all tradable goods."
    )
