"""Scored action models — wrap valid actions with cost/reward/risk scores."""
from pydantic import BaseModel, Field

from src.models.action import ActionState
from src.models.environment import ValidStepsState


class ScoredActionState(BaseModel):
    """A valid action paired with its scoring breakdown."""
    action: ActionState = Field(description="The action being scored.")
    score: float = Field(0.0, description="direct_score + projected_score - risk_score")
    direct_score: float = Field(0.0, description="Direct score for this action.")
    pipeline_score: float = Field(0.0, description="Projected score for this action.")
    risk_score: float = Field(0.0, description="Risk score for this action")


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