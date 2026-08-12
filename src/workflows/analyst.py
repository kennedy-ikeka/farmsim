from langgraph.graph import END
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableParallel

from src.utils.tool_set import ToolSet
from src.workflows.farmer import FarmerWorkflow
from src.workflows.purchaser import PurchaserWorkflow
from src.workflows.seller import SellerWorkflow
from src.models.game import RealityState, ProposalState, StrategyState
from src.utils.llms import get_llm
from src.models.workflow import WorkflowSettings
from src.models.workflow import BaseAgent

class AnalystState(BaseModel):
    """State model for the supervisor agent.

    Attributes:
        game_state: The game_state we exist in
    """
    game_state: RealityState = Field(default_factory=RealityState, description='The current state of the game')
    proposals: dict[str, ProposalState] = Field(default_factory=dict, description='The proposals by the spacialists')
    stratagy: StrategyState = Field(default_factory=StrategyState, description='The overall strategy')

class AnalystWorkflow(BaseAgent):
    # Action type tags that belong in the `market` slot of a StepState.

    def __init__(self, settings=WorkflowSettings()):
        super().__init__(AnalystState, settings)
        self._build_graph()
        self._llm = get_llm(temperature=self.settings.temperature)

    def _build_graph(self):
      self.add_node(self.ANALYZE, self.analyze)

      self.set_entry_point(self.ANALYZE)
      self.add_edge(self.ANALYZE, END)

      self.graph = self.compile(checkpointer=MemorySaver())

    ANALYZE = 'analyze'
    def analyze(self, state: AnalystState):
      farmer = FarmerWorkflow()
      purchaser = PurchaserWorkflow()
      seller = SellerWorkflow()

      parallel = RunnableParallel(steps={
        "farmer": farmer.as_tool(ToolSet.Farmer).tool,
        "purchaser": purchaser.as_tool(ToolSet.Purchaser).tool,
        "seller": seller.as_tool(ToolSet.Seller).tool,
      })

      input_data = {
        "objective": state.stratagy.objective,
        "game_state": state.game_state,
      }

      result = parallel.invoke(input_data)
      state.proposals = result['steps']
      return state
    
    def invoke(self, query: str, state: AnalystState) -> AnalystState:
        """Invoke the agent graph and return the response.

        Args:
            state: Initial support state

        Returns:
            Generated response string
        """
        state.messages.append(HumanMessage(query))
        return self.graph.invoke(state, config=self.settings.config)
