from pydantic import BaseModel, Field
from typing_extensions import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from src.models.game import RealityState, ProposalState
from src.models.workflow import AgentToolState, BaseWorkflow, WorkflowSettings
from src.utils.llms import get_llm
from langchain_core.tools import StructuredTool


class FarmerState(BaseModel):
    """State for generating a farm-related proposal."""

    objective: str = Field(..., description="The main objective to pursue")
    game_state: RealityState = Field(..., description="The current game state")
    proposal: Optional[ProposalState] = Field(
        default=None,
        description="The generated proposal"
    )


class FarmerWorkflow(BaseWorkflow):
    """Workflow for generating farm related proposals by farmer."""

    def __init__(self, settings=WorkflowSettings()):
        """Initialize the proposal workflow.

        Args:
            settings: Workflow configuration settings
        """
        super().__init__(state_schema=FarmerState, settings=settings)
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph with propose node."""
        self.add_node(self.PROPOSE, self.propose)

        self.set_entry_point(self.PROPOSE)
        self.set_finish_point(self.PROPOSE)

        self.graph = self.compile()

    PROPOSE = "propose"
    def propose(self, state: FarmerState) -> FarmerState:
        """Generate a proposal of the conversation.

        Args:
            settings: Workflow configuration settings

        Returns:
            Generated proposal
        """

        prompt = """
        You are the Kaggriculture Farm Specialist.

        You are responsible exclusively for farm operations:
        planting, watering, harvesting, fertilizing, weed removal, structures,
        animal care, feeding, fertilizer collection, and movement required to
        perform those operations.


        TASK

        Analyze the current player's farm and produce one PlanProposal that best
        advances the given objective.

        Prioritize actions that directly support the objective. When multiple farm
        operations could support it, prioritize them in this order:

        1. Prevent irreversible losses.
        - Water plants that risk becoming weeds.
        - Feed animals that risk escaping.

        2. Harvest ready resources when doing so supports the objective.

        3. Perform profitable crop or animal operations that support the objective.

        4. Remove weeds or prepare tiles when necessary for the objective.

        5. Plant or expand production when resources and available space justify it.


        RULES

        - Your proposal must pursue the given objective.
        - Only propose farm operations within your responsibility.
        - Do not buy or sell anything.
        - Do not hire workers.
        - Do not buy land.
        - Use only valid farm actions.
        - Use only resources visible in the current game state.
        - Never invent resources, prices, workers, positions, or tile contents.
        - Include movement actions when required to perform an operation.
        - Do not propose actions outside the current player's farm operations.
        - Keep the proposal focused on the single most valuable way to advance
        the objective.


        INPUT

        Objective:
        {objective}

        Current game state:
        {game_state}


        OUTPUT

        Return exactly one ProposalState with these fields in json format:
        {{
            "objective": "string" (the objective this proposal addresses),
            "recommendation": "string" (the recommended purchase approach for advancing the objective),
            "priority": 1 (importance of this proposal, integer >= 1 (lower means higher priority)
        }}

        Do not include explanations, Markdown, code fences, or fields outside the
        ProposalState schema.
        """

        formatted_prompt = prompt.format(objective=state.objective, game_state=state.game_state)
        message = [SystemMessage(content=formatted_prompt), HumanMessage(content="Generate proposal that fits the objective")]

        llm = get_llm().with_structured_output(ProposalState)

        response = llm.invoke(message)
        return {"proposal": response}

    def invoke(self, state: FarmerState) -> ProposalState:
        """Execute the workflow and return proposal.

        Args:
            state: Initial proposal state

        Returns:
            Generated conversation proposal
        """
        super().invoke(state)
        response = self.graph.invoke(state, config=self.settings.config)
        self.logger.info('Invoked!')
        return response['proposal']

    def as_tool(self, name: str) -> AgentToolState:
        tool = StructuredTool.from_function(
            name=name,
            description=(
                "Analyze the current player's farm and generate a proposal for "
                "farm operations such as planting, watering, harvesting, animal care, "
                "weeding, fertilizing, structures, and movement."
            ),
            func=lambda objective, game_state: self.invoke(
                FarmerState(
                    objective=objective,
                    game_state=game_state,
                )
            ),
        )

        return AgentToolState(
            action="Farmer Proposing",
            tool=tool,
        )