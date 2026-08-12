import json

from langgraph.graph import END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import Annotated

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableParallel

from src.workflows.informant import InformantWorkflow
from src.utils.tool_set import ToolSet
from src.workflows.farmer import FarmerWorkflow
from src.workflows.purchaser import PurchaserWorkflow
from src.workflows.seller import SellerWorkflow
from src.models.environment import StepState
from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.models.game import RealityState, ProposalState, StrategyState
from src.utils.llms import get_llm
from src.models.workflow import WorkflowSettings
from src.models.workflow import BaseAgent

class SupervisorState(BaseModel):
    """State model for the supervisor agent.

    Attributes:
        messages: Conversation history messages
        game_state: The game_state we exist in
    """
    messages: Annotated[list[AnyMessage], add_messages] = Field([], description='The conversation history')
    game_state: RealityState = Field(default_factory=RealityState, description='The current state of the game')
    proposals: dict[str, ProposalState] = Field(default_factory=dict, description='The proposals by the spacialists')
    stratagy: StrategyState = Field(default_factory=StrategyState, description='The agents strategy')
    steps: list[StepState] = Field(default_factory=list, description='The list of steps played')
    analyzed_day: int = Field(default=-1, description='The in-game day on which proposals were last generated. -1 means never analyzed.')

class SupervisorAgent(BaseAgent):
    # Action type tags that belong in the `market` slot of a StepState.

    def __init__(self, settings=WorkflowSettings()):
        super().__init__(SupervisorState, settings)
        self._build_graph()
        self._llm = get_llm(temperature=self.settings.temperature)

    def should_analyze(self, state: SupervisorState):
      # Re-run specialists only at the start of a new in-game day.
      if state.analyzed_day != state.game_state.day:
          return self.ANALYZE
      return self.PLAY

    def _build_graph(self):
      self.add_node(self.ANALYZE, self.analyze)
      self.add_node(self.PLAY, self.play)

      self.set_conditional_entry_point(
        self.should_analyze,
        {self.ANALYZE: self.ANALYZE, self.PLAY: self.PLAY},
      )
      self.add_edge(self.ANALYZE, self.PLAY)
      self.add_edge(self.PLAY, END)

      self.graph = self.compile(checkpointer=MemorySaver())

    ANALYZE = 'analyze'
    def analyze(self, state: SupervisorState):
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
      state.analyzed_day = state.game_state.day
      return state

    PLAY = 'play'
    def play(self, state: SupervisorState) -> SupervisorState:
      """Turn the specialist proposals into the next executable step.

      Reads the proposals produced by the ANALYZE node and the current game
      state, then emits a single StepState for this turn: one farm action for
      the farmer, one per hired hand, and up to MAX_MARKET_ORDERS_PER_TURN
      market actions. The produced step is appended to `state.steps`.
      """
      play_prompt = """
      You are the Kaggriculture Actor.

      You turn the specialist proposals into the concrete StepState the player
      will submit this turn. You do not revise the strategy — you execute it.


      TASK

      Read the specialist proposals (farmer, purchaser, seller) and the current
      game state, then emit one StepState that best advances the objective this
      turn. Select, combine, or reject proposals based on their value toward
      the objective, resolve conflicts, respect dependencies, and prioritize
      urgent actions that prevent irreversible losses before profitable
      operations.

      A StepState has three slots:
      * farmer: exactly ONE farm action for the farmer (a single unit that
        acts once this turn). If no farm action advances the objective, emit
        {{"type": "PASS"}}.
      * hands: ONE farm action per hired hand, in the same order as
        farms[player].hands. A hand at position (r, c) acts from that tile.
        If a hand has nothing useful to do, emit {{"type": "PASS"}} for it.
        Do not emit more entries than there are hired hands; do not emit
        market actions here.
      * market: zero or more market actions, at most {max_orders} in total,
        ordered by priority (time-sensitive before routine). Market actions
        are queued and processed one unit at a time across players, so a
        SELL of count 10 may partially fill if shared inventory or money runs
        out. If no market action is needed this turn, emit an EMPTY list for
        `market` (`[]`). Never emit placeholder entries, blank type tags, or
        actions outside the catalog below.


      RULES

      - The step must advance the objective and respect the proposals.
      - Use only valid actions from the catalog below.
      - Use only resources, prices, and capacities visible in the current
        game state.
      - Never invent resources, prices, workers, positions, or tile contents.
      - `count` is always an integer > 0 and must not exceed what the player
        can hold, afford, or has in the shed.
      - Crops are "WHEAT" | "CARROT" | "TOMATO" | "STRAWBERRY" | "MELON".
      - Animals are "GOOSE" | "COW" | "SHEEP".
      - Sellable products are "WHEAT" | "CARROT" | "TOMATO" | "STRAWBERRY" |
        "MELON" | "EGG" | "MILK" | "WOOL" | "FERTILIZER".
      - Buyable-back products are "WHEAT" | "FERTILIZER".
      - Prefer daily obligations first: WATER any plant not yet watered today,
        FEED any animal not yet fed today, CARE any animal not yet cared for
        today. Missing two days kills the plant or loses the animal.
      - Keep the step focused on the single most valuable way to advance the
        objective this turn.


      ACTION CATALOG

      Farmer / Farm Hand actions (one per acting unit, position-based):
      * {{"type": "PASS"}}                                  — do nothing this turn
      * {{"type": "NORTH"}} | "SOUTH" | "EAST" | "WEST"   — move one cell
      * {{"type": "PLANT", "crop": <crop>}}                — plant a seed on the current tile
      * {{"type": "WATER"}}                               — water the plant on the current tile (once per day)
      * {{"type": "HARVEST"}}                             — harvest the plant / animal on the current tile into the shed
      * {{"type": "FERTILIZE"}}                           — fertilize the plant on the current tile (doubles watering bonus for 3 days)
      * {{"type": "DIG"}}                                 — remove a plant / weed / empty structure from the current tile
      * {{"type": "BUILD_COOP"}}                          — erect an empty goose coop on the current tile
      * {{"type": "BUILD_PASTURE"}}                       — erect an empty pasture on the current tile
      * {{"type": "FEED"}}                                — feed the housed animal one wheat (once per day)
      * {{"type": "COLLECT_FERTILIZER"}}                  — collect 1 fertilizer from the housed animal
      * {{"type": "CARE"}}                                — mark the housed animal cared-for today (once per day)
      * {{"type": "PICKUP", "item": <item>, "count": <n>}} — pick up n of <item> from the shed into inventory (shed-adjacent)
      * {{"type": "PLACE", "item": <item>, "count": <n>}} — place n of <item> from inventory onto a tile or into the shed

      Market actions (only in the `market` list):
      * {{"type": "BUY_SEED", "crop": <crop>, "count": <n>}}    — buy n seeds of <crop> at the fixed seed cost
      * {{"type": "BUY_PRODUCT", "item": "WHEAT"|"FERTILIZER", "count": <n>}} — buy n of <item> back from market inventory
      * {{"type": "BUY_ANIMAL", "animal": <animal>, "count": <n>}} — buy n <animal>; PLACE onto a matching structure to house
      * {{"type": "SELL", "item": <sellable>, "count": <n>}}    — sell n of <item> from the shed to the market at the current price
      * {{"type": "HIRE"}}                                        — hire one farm hand for the day (Fibonacci cost)
      * {{"type": "BUY_LAND"}}                                    — unlock the next quadrant (NE $1k -> SW $2k -> SE $4k)


      INPUT

      Current game state:
      {game_state}

      Specialist proposals:
      {proposals}

      Current strategy:
      {strategy}


      OUTPUT

      Return exactly one StepState.
      Do not include explanations, Markdown, code fences, or fields outside the
      StepState schema.
      """

      formatted_prompt = play_prompt.format(
          game_state=state.game_state,
          proposals=state.proposals,
          strategy=state.stratagy,
          max_orders=MAX_MARKET_ORDERS_PER_TURN,
      )
      message = [SystemMessage(content=formatted_prompt), HumanMessage(content="Generate the next step based on the proposals")]
      self.logger.info("Playing...")

      tooled_llm = self._llm.with_structured_output(StepState)
      response = tooled_llm.invoke(message)
      state.steps.append(response)
      return state

    def invoke(self, query: str, state: SupervisorState) -> SupervisorState:
        """Invoke the agent graph and return the response.

        Args:
            state: Initial support state

        Returns:
            Generated response string
        """
        super().invoke(state)
        state.messages.append(HumanMessage(query))
        response = self.graph.invoke(state, config=self.settings.config)
        self.logger.info('Invoked!')
        return response
