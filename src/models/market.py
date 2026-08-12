from pydantic import BaseModel, Field


class MarketInventory(BaseModel):
    """Quantities of goods currently available in the market."""

    WHEAT: int = Field(10_000, description="Wheat units available for purchase.")
    CARROT: int = Field(10_000, description="Carrot units available for purchase.")
    TOMATO: int = Field(10_000, description="Tomato units available for purchase.")
    STRAWBERRY: int = Field(10_000, description="Strawberry units available for purchase.")
    MELON: int = Field(10_000, description="Melon units available for purchase.")
    EGG: int = Field(10_000, description="Egg units available for purchase.")
    MILK: int = Field(10_000, description="Milk units available for purchase.")
    WOOL: int = Field(10_000, description="Wool units available for purchase.")
    FERTILIZER: int = Field(10_000, description="Fertilizer units available for purchase.")


class MarketPrices(BaseModel):
    """Current market price of each tradable item."""

    WHEAT: int = Field(25, description="Current market price of one unit of wheat.")
    CARROT: int = Field(35, description="Current market price of one unit of carrots.")
    TOMATO: int = Field(60, description="Current market price of one unit of tomatoes.")
    STRAWBERRY: int = Field(120)
    MELON: int = Field(250, description="Current market price of one unit of melons.")
    EGG: int = Field(50, description="Current market price of one unit of eggs.")
    MILK: int = Field(160, description="Current market price of one unit of milk.")
    WOOL: int = Field(200, description="Current market price of one unit of wool.")
    FERTILIZER: int = Field(100, description="Current market price of one unit of fertilizer.")


class MarketState(BaseModel):
    """Current state of the game's marketplace."""

    inventory: MarketInventory = Field(
        default_factory=MarketInventory,
        description="Available quantities of tradable goods."
    )

    prices: MarketPrices = Field(
        default_factory=MarketPrices,
        description="Current prices for all tradable goods."
    )
