"""Timeline model — configuration state for the environment's time + day refresh.

Holds the knobs that the `Timeline` controller consults when advancing the in-game
clock and running the end-of-day refresh. Defaults are sourced from
`src.utils.config` so a bare `TimelineState()` matches the documented game
constants; callers may override any field to vary episode length, day length,
shed capacity, or weed-spawn rate per environment.
"""
from pydantic import BaseModel, Field

from src.utils.config import (
    EPISODE_STEPS,
    SHED_CAPACITY,
    TURNS_PER_DAY,
    WEED_SPAWN_CHANCE,
)


class ClockState(BaseModel):
    """Configuration for the environment's time advancement and day refresh."""

    turns_per_day: int = Field(
        default=TURNS_PER_DAY,
        description="Steps that make up one in-game day.",
    )
    episode_steps: int = Field(
        default=EPISODE_STEPS,
        description="Total steps in a full episode; the done flag trips here.",
    )
    shed_capacity: int = Field(
        default=SHED_CAPACITY,
        description="Maximum units a player's shed can hold across all items.",
    )
    weed_spawn_chance: float = Field(
        default=WEED_SPAWN_CHANCE,
        description="Per-empty-tile probability of a weed spawning at end of day.",
    )