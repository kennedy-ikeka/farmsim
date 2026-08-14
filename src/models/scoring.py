"""Scored action models — wrap valid actions with cost/reward/risk scores."""
from pydantic import BaseModel, Field

from src.models.action import ActionState
from src.models.environment import ValidStepsState


class ScoredActionState(BaseModel):
    """A valid action paired with its scoring breakdown."""
    action: ActionState = Field(description="The action being scored.")
    score: float = Field(0.0, description="Final score = reward - (cost + risk) / 2.")
    cost_score: float = Field(0.0, description="Resources consumed by this action.")
    reward_score: float = Field(0.0, description="Resources gained by this action.")
    risk_score: float = Field(0.0, description="Probability-weighted risk of action not bearing fruit.")


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