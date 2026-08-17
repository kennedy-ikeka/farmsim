"""Scored action models — wrap valid actions with cost/reward/risk scores."""
from pydantic import BaseModel, Field

from src.models.action import ActionState
from src.models.environment import ValidStepsState


class ScoredActionState(BaseModel):
    """A valid action paired with its scoring breakdown."""
    action: ActionState = Field(description="The action being scored.")
    score: float = Field(0.0, description="(reward - cost) + (future_reward - future_cost) * FUTURE_DISCOUNT_RATE.")
    cost_score: float = Field(0.0, description="Immediate resources consumed by this action.")
    reward_score: float = Field(0.0, description="Immediate resources gained by this action.")
    future_cost_score: float = Field(0.0, description="Future resources spent to realize the deferred payoff.")
    future_reward_score: float = Field(0.0, description="Deferred resources this action enables (realized downstream).")


class ScoredValidStepsState(BaseModel):
    """Mirrors ValidStepsState but with scored actions."""
    farmer: list[ScoredActionState] = Field(
        default_factory=list,
        description="The farmer's valid actions, scored."
    )
    hands: list[list[ScoredActionState]] = Field(
        default_factory=list,
        description="Per-hand scored valid actions."
    )
    market: list[ScoredActionState] = Field(
        default_factory=list,
        description="Scored valid market actions."
    )