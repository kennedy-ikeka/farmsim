from typing_extensions import Literal
import uuid

from pydantic import BaseModel, Field

from src.models.action import ActionState
from src.models.farm import FarmState
from src.models.market import MarketState
from src.models.player import PrivateState
from src.models.town import TownState

PLAN_STATUS = Literal["PENDING", 'ACTIVE', 'COMPLETED', 'BLOCKED', 'ABANDONED']
TARGET_METRICS = Literal["MONEY"]
TARGET_OPERATIONS = Literal["EQ", "GTE", "LTE", "GT", "LT"]

class GameState(BaseModel):
    """Full two-player game state — the authoritative world the controllers mutate.

    This is the full-game state (not the per-agent observation). The
    `Environment` controller owns one `GameState` and steps it in place.
    `player` is the active-player pointer: during step iteration the
    environment sets it to the index of the player whose actions are being
    applied, so action modules can read `state.privates[state.player]` and
    `state.farms[state.player]` without an explicit player argument.

    `privates` is indexed by player id (length 2 in a standard episode).
    `farms` parallels `privates` — one farm per player. `market` and `town`
    are shared across both players. The agent-facing observation (README
    "Observation Format") is a per-player view projected from this state;
    building that view is a separate concern.
    """

    remainingOverageTime: float = Field(
        description=("Remaining computation/time allowance available to the player for the current game state.")
    )

    step: int = Field(
        description="Current simulation step or turn number."
    )

    day: int = Field(
        description="Current in-game day."
    )

    hour: int = Field(
        description="Current in-game hour."
    )

    player: int = Field(
        description="Identifier of the player whose turn/state is being represented."
    )

    farms: list[FarmState] = Field(
        description="All farms belonging to the players in the game."
    )

    market: MarketState = Field(
        description="Public marketplace state, including inventory and prices."
    )

    town: TownState = Field(
        description="Current state of the town and its available shops."
    )


class PrivateGameState(GameState):
    private: PrivateState = Field(
        default_factory=PrivateState, 
        description='Current players private state'
    )


class PublicGameState(GameState):
    privates: list[PrivateState] = Field(
            default_factory=list,
            description="Per-player private state, indexed by player id."
    )


class TargetState(BaseModel):
    """A measurable goal a `Plan` aims to reach.

    A target pairs a `metric` (currently only MONEY — the player's bank
    balance) with a comparison `operation` and a `value`, e.g.
    `MONEY GTE 5000` reads "the player has at least $5000 banked".
    """

    metric: TARGET_METRICS = Field('MONEY', description="The metric this target measures")
    operation: TARGET_OPERATIONS = Field('EQ', description="The operation to measure the metric")
    value: float = Field(3000, description="The value to measure the current state of the target")


class PlanState(BaseModel):
    """A single prioritized intention an agent may pursue.

    Plans are an agent-side abstraction — they live outside the simulation
    and are not mutated by `Environment.step`. A plan bundles an `objective`
    (free-form description of the intent), an ordered list of candidate
    `actions` the plan may dispatch, a `target` it aims to reach, and a
    lifecycle `status`. `priority` orders competing plans (1 = highest).
    `id` is a generated uuid hex so plans can be referenced across
    executions without identity-by-value.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="The id of the plan")
    priority: int = Field(1, ge=1, description="The importance of this plan to the goal")
    objective: str = Field("", description="The main purpose of this plan")
    actions: list[ActionState] = Field(default_factory=list, description="Actions this plan may implement")
    target: TargetState = Field(default_factory=TargetState, description="The target for the plan")
    status: PLAN_STATUS = Field('PENDING', description="The status of the plan")

class ProposalState(BaseModel):
    """A specialist recommendation for advancing an objective."""

    objective: str = Field(
        description="The objective this proposal addresses."
    )

    recommendation: str = Field(
        description="The recommended approach for advancing the objective."
    )

    reasoning: str = Field(
        description="Why this recommendation is appropriate given the current state."
    )

    priority: int = Field(
        ge=1,
        description="Importance of this proposal. Lower means higher priority."
    )

    expected_outcome: str = Field(
        description="The expected result if this recommendation is implemented."
    )

    constraints: list[str] = Field(
        default_factory=list,
        description="State-dependent limitations or requirements affecting implementation."
    )

    risks: list[str] = Field(
        default_factory=list,
        description="Potential losses or consequences of not addressing this proposal."
    )

class ExecutionState(BaseModel):
    """Placeholder record of a single attempt to execute a `Plan`.

    Intended to capture the outcome of dispatching one of a plan's candidate
    actions against the game state (which action ran, what it produced,
    whether the target advanced). Currently an empty model — fields will
    be added as the execution-tracking layer is built out.
    """

    ...


class GamePlanState(BaseModel):
    """The set of plans an agent intends to pursue on a given in-game day.

    Groups the `Plan`s active for `day` together with their `PlanExecution`
    records, so an agent can review what it intended vs. what happened on
    that day and revise the next day's plans accordingly.
    """

    day: int = Field(0, description="The day for this game plan")
    plans: list[PlanState] = Field(default_factory=list, description="The plans to be executed")

class StrategyState(BaseModel):
    """The player's current strategy."""

    objective: str = Field(
        "Win the game",
        description="The primary objective currently being pursued."
    )

    instructions: list[str] = Field(
        default_factory=list,
        description="Instructions that guide the Actor's decisions."
    )