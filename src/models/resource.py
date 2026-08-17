from pydantic import BaseModel, Field


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
    PRODUCE: float = Field(1.0, description="Weight for produce in action scoring.")


class ResourceState(BaseModel):
    """Per-resource weights used when scoring actions.

    Each weight multiplies the `(usage / available)` term for that resource in
    the cost and reward scores. Defaults are 1.0 so every resource is valued
    equally out of the box; override individual fields to bias scoring (e.g.
    bump `STEP` to penalize turn-spending, or `MONEY` to be thriftier).
    """

    MONEY: float = Field(0, description="Value for money in action scoring.")
    STEP: float = Field(0, description="Value for step/turn usage in action scoring.")
    SEED: float = Field(0, description="Value for seed value in action scoring.")
    LAND: float = Field(0, description="Value for empty land tiles in action scoring.")
    ANIMAL: float = Field(0, description="Value for animal value in action scoring.")
    HAND: float = Field(0, description="Value for hired hands in action scoring.")
    PRODUCE: float = Field(0, description="Value for produce in action scoring.")
