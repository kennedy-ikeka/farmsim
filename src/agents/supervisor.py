import json

from langgraph.graph import END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import Annotated

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver

from src.workflows.informant import InformantWorkflow
from src.utils.tool_set import ToolSet
from src.workflows.farmer import FarmerWorkflow
from src.workflows.purchaser import PurchaserWorkflow
from src.workflows.seller import SellerWorkflow
from src.models.environment import StepState
from src.utils.config import MAX_MARKET_ORDERS_PER_TURN
from src.models.game import GamePlanState, PrivateGameState, StrategyState
from src.utils.llms import get_llm
from src.models.workflow import WorkflowSettings
from src.models.workflow import BaseAgent

TERMINAL_PLAN_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "ABANDONED",
}

class SupervisorState(BaseModel):
    """State model for the supervisor agent.

    Attributes:
        messages: Conversation history messages
        game_state: The game_state we exist in
    """
    messages: Annotated[list[AnyMessage], add_messages] = Field([], description='The conversation history')
    game_state: PrivateGameState = Field(default_factory=PrivateGameState, description='The current state of the game')
    game_plan: GamePlanState = Field(default_factory=GamePlanState, description='The generated game plan')
    stratagy: StrategyState = Field(default_factory=StrategyState, description='The agents strategy')
    steps: list[StepState] = Field(default_factory=list, description='The list of steps played')

class SupervisorAgent(BaseAgent):
    # Action type tags that belong in the `market` slot of a StepState.
    MARKET_TYPES = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}

    def __init__(self, settings=WorkflowSettings()):
        super().__init__(SupervisorState, settings)
        self.set_tools()
        self.tool_model = ToolNode(self.tools)
        self._build_graph()

    TOOL_MODEL = 'tools'
    def set_tools(self):
        """Configure and register all available tools for the agent.

        Initializes workflows for search, enhancement, evaluation,
        and document extraction.
        """
        # self.agent_memory = AgentMemory(session_id=self.settings.session_id)

        informant = InformantWorkflow(['farm_docs', 'farm_data'], settings=self.settings)
        farmer = FarmerWorkflow()
        purchaser = PurchaserWorkflow()
        seller = SellerWorkflow()

        tools = [
            farmer.as_tool(ToolSet.Farmer),
            purchaser.as_tool(ToolSet.Purchaser),
            seller.as_tool(ToolSet.Seller),
            informant.as_tool(ToolSet.Informant)
        ]

        self.tools = []
        self.tool_actions = {}
        self.skill_set = []

        for item in tools:
            self.tools.append(item.tool)
            self.skill_set.append(f"- {item.tool.name}: {item.tool.description}")
            self.tool_actions[item.tool.name] = item.action

    def should_plan(self, state: SupervisorState):
      game_plan = state.game_plan

      # No meaningful plan exists yet.
      if not len(game_plan.plans):
          return self.PLAN

      # Replan only when every plan is finished
      # all_completed = all(
      #     plan.status in TERMINAL_PLAN_STATUSES
      #     for plan in game_plan
      # )

      # if all_completed:
      #     return self.PLAN

      # Continue executing / following the existing plan.
      return self.PLAY

    def _build_graph(self):
        self.add_node(self.PLAN, self.plan)
        self.add_node(self.TOOL_MODEL, self.tool_model)
        self.add_node(self.PLAY, self.play)

        self.set_conditional_entry_point(
            self.should_plan,
            [self.PLAN, self.PLAY],
        )
            
        self.add_conditional_edges(
          self.PLAN, 
          tools_condition, 
          [self.TOOL_MODEL, self.PLAY]
        )

        self.add_edge(self.TOOL_MODEL, self.PLAN)
        self.add_edge(self.PLAY, END)

        self.graph = self.compile(checkpointer=MemorySaver())

    PLAN = 'plan'
    def plan(self, state: SupervisorState) -> SupervisorState:
      play_prompt = """
      You are an autonomous Kaggriculture player.

      Your goal is to maximize your bank balance by the end of the season. You make
      strategic decisions based on the current game state and use available tools to
      analyze relevant domains.

      You are the decision-maker. Specialist tools provide expertise, but you decide
      the player's overall strategy.


      TASK

      Analyze the current game situation and produce the player's GamePlan.

      The GamePlan defines:
      - the primary objective currently being pursued,
      - concise instructions that guide the player's future decisions.

      Use specialist tools when their expertise is relevant to the current situation.

      Available tools:
      {skill_set}

      You may call tools multiple times when necessary. Use their results together
      with the current game state to determine the best strategy.


      RULES

      - The ultimate goal is to finish the season with the highest bank balance.
      - Balance immediate profit against future productivity.
      - Prevent avoidable losses when they materially threaten future value.
      - Base decisions only on the current game state and information returned by tools.
      - Do not invent resources, prices, player information, tile contents, or future
        outcomes.
      - You can observe both players' public game state, including farms, the shared
        market, town, and game time.
      - You can only access this player's private state.
      - Never assume knowledge of the opponent's private inventory, shed, seeds, or
        other hidden state.
      - Consult relevant specialists instead of duplicating their detailed domain
        reasoning.
      - Treat specialist outputs as advice and evidence, not unquestionable commands.
      - Choose the final strategy yourself.
      - Do not generate executable game actions or StepStates.
      - Keep the GamePlan concise and focused.
      - The objective should describe the most important outcome to pursue.
      - Instructions should be clear strategic guidance that a smart Actor can use to
        decide actions from the current state.
      - Revise the existing GamePlan when the current state makes its objective or
        instructions no longer appropriate.


      INPUT

      Current game state:
      {game_state}

      Current GamePlan:
      {game_plan}


      OUTPUT

      Return exactly one GamePlanState containing:

      - objective: the primary outcome currently being pursued.
      - instructions: a short list of strategic instructions that guide the Actor.

      Do not include explanations, Markdown, code fences, executable actions, or
      fields outside the GamePlanState schema.
      """
      formatted_prompt = play_prompt.format(
          game_state=state.game_state,
          game_plan=state.game_plan,
          skill_set=self.skill_set
      )
      system_message = SystemMessage(content=formatted_prompt)
      llm = get_llm(temperature=self.settings.temperature).bind_tools(self.tools).with_structured_output(GamePlanState)

      self.logger.info("Planning...")
      response = llm.invoke(
          [system_message] + state.messages
      )
      state.steps.append(response)
      return state

    PLAY = 'play'
    def play(self, state: SupervisorState) -> SupervisorState:
        """Turn the current game plan into the next executable step.

        Reads the GamePlan (strategy + plans) produced by the PLAN node and the
        current game state, then emits a single StepState for this turn: one
        farm action for the farmer, one per hired hand, and up to
        MAX_MARKET_ORDERS_PER_TURN market actions. The produced step is
        appended to `state.steps`.
        """
        play_prompt = """
        You are the Kaggriculture Actor.

        You turn the player's current GamePlan into the concrete StepState the
        player will submit this turn. You do not revise the strategy — you
        execute it.


        TASK

        Read the current GamePlan (objective + instructions + plans) and the
        current game state, then emit one StepState that best advances the
        objective this turn while following the plan's instructions.

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
          out.


        RULES

        - The step must advance the GamePlan's objective and follow its
          instructions.
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

        Current GamePlan:
        {game_plan}

        Current strategy:
        {strategy}


        OUTPUT

        Return exactly one StepState.
        Do not include explanations, Markdown, code fences, or fields outside the
        StepState schema.
        """

        formatted_prompt = play_prompt.format(
            game_state=state.game_state,
            game_plan=state.game_plan,
            strategy=state.stratagy,
            max_orders=MAX_MARKET_ORDERS_PER_TURN,
        )
        system_message = SystemMessage(content=formatted_prompt)
        llm = get_llm(temperature=self.settings.temperature).with_structured_output(StepState)

        self.logger.info("Playing...")
        response = llm.invoke([system_message] + state.messages)
        state.steps.append(response)
        return state

    def invoke(self, query: str, state: SupervisorState) -> SupervisorState:
        """Invoke the agent graph and return the response.

        Args:
            state: Initial support state

        Returns:
            Generated response string
        """
        state.messages.append(HumanMessage(query))
        return self.graph.invoke(state, config=self.settings.config)
