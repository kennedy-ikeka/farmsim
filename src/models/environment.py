from enum import Enum
from typing import Optional
from typing_extensions import Literal

from pydantic import BaseModel, Field


from pydantic import BaseModel, Field


class MoveState(BaseModel):
    """The next set of actions for the farm."""

    farmer: dict = Field(
        default_factory=lambda: {"action": "Pass"},
        description="The farmer's next action."
    )

    hands: list[dict] = Field(
        default_factory=list,
        description="The next actions assigned to hired workers."
    )

    market: list[dict] = Field(
        default_factory=list,
        description="The next market actions."
    )


class EnvironmentState(BaseModel):
    ...