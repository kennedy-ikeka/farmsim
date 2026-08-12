from pydantic import BaseModel, Field
from typing_extensions import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from src.models.game import PrivateGameState, ProposalState
from src.models.workflow import AgentToolState, BaseWorkflow, WorkflowSettings
from src.utils.llms import get_llm
from langchain_core.tools import StructuredTool


class SellerState(BaseModel):
    """State for generating a sell-related proposal."""

    objective: str = Field(..., description="The main objective to pursue")
    game_state: PrivateGameState = Field(..., description="The current game state")
    proposal: Optional[ProposalState] = Field(
        default=None,
        description="The generated proposal"
    )


class SellerWorkflow(BaseWorkflow):
    """Workflow for generating market sell proposals by the seller."""

    def __init__(self, settings=WorkflowSettings()):
        """Initialize the seller workflow.

        Args:
            settings: Workflow configuration settings
        """
        super().__init__(state_schema=SellerState, settings=settings)
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph with propose node."""
        self.add_node(self.PROPOSE, self.propose)

        self.set_entry_point(self.PROPOSE)
        self.set_finish_point(self.PROPOSE)

        self.graph = self.compile()

    PROPOSE = "propose"
    def propose(self, state: SellerState) -> SellerState:
        """Generate a sell proposal for the given objective.

        Args:
            state: Current workflow state with objective and game state

        Returns:
            State carrying the generated proposal
        """

        prompt = """
        You are the Kaggriculture Seller Specialist.

        You are responsible exclusively for selling harvested produce from the
        player's shed to the shared market. You do not buy, and you do not perform
        farm operations.


        TASK

        Analyze the current player's shed inventory and the market prices, then
        produce one PlanProposal that best advances the given objective through
        sales.

        Prioritize sales that directly support the objective. When multiple sales
        could support it, prioritize them in this order:

        1. Sell into favorable prices before the market glut drives prices to floor.
        - Sell products whose current market price is above their typical floor.

        2. Clear perishable or accumulating inventory before it loses value or
        blocks shed capacity.

        3. Hold inventory when the current price is unfavorable and storage
        capacity allows waiting for a better price.


        RULES

        - Your proposal must pursue the given objective.
        - Only propose sell operations within your responsibility.
        - Do not propose buying.
        - Do not propose farm operations (planting, watering, movement, etc.).
        - Use only valid sell actions.
        - Use only resources and prices visible in the current game state.
        - Never invent resources, prices, or future outcomes.
        - Respect the player's current shed inventory; do not propose selling more
          of an item than the player holds.
        - Keep the proposal focused on the single most valuable way to advance the
          objective through sales.


        VALID SELL ACTION

        * {{"type": "SELL", "item": <sellable>, "count": <n>}} — sell n of <item>
          from the shed to the market at the current price

        Sellable products are "WHEAT" | "CARROT" | "TOMATO" | "STRAWBERRY" |
        "MELON" | "EGG" | "MILK" | "WOOL" | "FERTILIZER".
        `count` is always an integer > 0.


        INPUT

        Objective:
        {objective}

        Current game state:
        {game_state}


        OUTPUT

        Return exactly one PlanProposal.
        Do not include explanations, Markdown, code fences, or fields outside the
        PlanProposal schema.
        """

        formatted_prompt = prompt.format(objective=state.objective, game_state=state.game_state)
        message = [SystemMessage(content=formatted_prompt), HumanMessage(content="Generate proposal that fits the objective")]

        llm = get_llm().with_structured_output(ProposalState)
        response = llm.invoke(message)

        return {"proposal": response}

    def invoke(self, state: SellerState) -> ProposalState:
        """Execute the workflow and return proposal.

        Args:
            state: Initial proposal state

        Returns:
            Generated conversation proposal
        """
        super().invoke(state)
        response = self.graph.invoke(state, config=self.settings.config)
        return response['proposal']

    def as_tool(self, name: str) -> AgentToolState:
        tool = StructuredTool.from_function(
            name=name,
            description=(
                "Analyze the current player's shed inventory and market prices and "
                "generate a proposal for selling harvested produce to the market, "
                "prioritizing favorable prices and clearing perishable inventory."
            ),
            func=lambda objective, game_state: self.invoke(
                SellerState(
                    objective=objective,
                    game_state=game_state,
                )
            ),
        )

        return AgentToolState(
            action="Seller Proposing",
            tool=tool,
        )