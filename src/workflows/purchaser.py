from pydantic import BaseModel, Field
from typing_extensions import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from src.models.game import PrivateGameState, ProposalState
from src.models.workflow import AgentToolState, BaseWorkflow, WorkflowSettings
from src.utils.llms import get_llm
from langchain_core.tools import StructuredTool


class PurchaserState(BaseModel):
    """State for generating a purchase-related proposal."""

    objective: str = Field(..., description="The main objective to pursue")
    game_state: PrivateGameState = Field(..., description="The current game state")
    proposal: Optional[ProposalState] = Field(
        default=None,
        description="The generated proposal"
    )


class PurchaserWorkflow(BaseWorkflow):
    """Workflow for generating market purchase proposals by the purchaser."""

    def __init__(self, settings=WorkflowSettings()):
        """Initialize the purchaser workflow.

        Args:
            settings: Workflow configuration settings
        """
        super().__init__(state_schema=PurchaserState, settings=settings)
        self._build_graph()

    def _build_graph(self):
        """Build the workflow graph with propose node."""
        self.add_node(self.PROPOSE, self.propose)

        self.set_entry_point(self.PROPOSE)
        self.set_finish_point(self.PROPOSE)

        self.graph = self.compile()

    PROPOSE = "propose"
    def propose(self, state: PurchaserState) -> PurchaserState:
        """Generate a purchase proposal for the given objective.

        Args:
            state: Current workflow state with objective and game state

        Returns:
            State carrying the generated proposal
        """

        prompt = """
        You are the Kaggriculture Purchaser Specialist.

        You are responsible exclusively for market purchase operations:
        buying seeds, buying back products (wheat and fertilizer), buying
        livestock, hiring farm hands, and buying land. You do not sell, and you
        do not perform farm operations.


        TASK

        Analyze the current player's market position and produce one PlanProposal
        that best advances the given objective through purchases.

        Prioritize purchases that directly support the objective. When multiple
        purchases could support it, prioritize them in this order:

        1. Buy inputs required to prevent irreversible losses.
        - Buy wheat to feed animals that risk escaping.
        - Buy fertilizer to sustain high-yield crops.

        2. Buy inputs for committed production when doing so supports the objective.
        - Buy seeds for crops the player intends to plant.

        3. Buy livestock when housing and feeding capacity justify it.

        4. Hire farm hands only when the marginal action earns more than the
        Fibonacci hire cost; hands drop inventory and leave at end of day.

        5. Buy land only when the player can profitably exploit the unlocked
        quadrant and the cost is justified.


        RULES

        - Your proposal must pursue the given objective.
        - Only propose market purchase operations within your responsibility.
        - Do not propose selling.
        - Do not propose farm operations (planting, watering, movement, etc.).
        - Use only valid purchase actions.
        - Use only resources, prices, and capacities visible in the current game
          state.
        - Never invent resources, prices, workers, or future outcomes.
        - Respect the player's current bank balance; do not propose purchases the
          player cannot afford.
        - Keep the proposal focused on the single most valuable way to advance the
          objective through purchases.


        VALID PURCHASE ACTIONS

        * {{"type": "BUY_SEED", "crop": <crop>, "count": <n>}}    — buy n seeds of <crop> at the fixed seed cost
        * {{"type": "BUY_PRODUCT", "item": "WHEAT"|"FERTILIZER", "count": <n>}} — buy n of <item> back from market inventory
        * {{"type": "BUY_ANIMAL", "animal": <animal>, "count": <n>}} — buy n <animal>; PLACE onto a matching structure to house
        * {{"type": "HIRE"}}                                      — hire one farm hand for the day (Fibonacci cost)
        * {{"type": "BUY_LAND"}}                                   — unlock the next quadrant (NE $1k -> SW $2k -> SE $4k)

        Crops are "WHEAT" | "CARROT" | "TOMATO" | "STRAWBERRY" | "MELON".
        Animals are "GOOSE" | "COW" | "SHEEP".
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

    def invoke(self, state: PurchaserState) -> ProposalState:
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
                "Analyze the current player's market position and generate a "
                "proposal for purchase operations such as buying seeds, buying back "
                "products, buying livestock, hiring farm hands, and buying land."
            ),
            func=lambda objective, game_state: self.invoke(
                PurchaserState(
                    objective=objective,
                    game_state=game_state,
                )
            ),
        )

        return AgentToolState(
            action="Purchaser Proposing",
            tool=tool,
        )