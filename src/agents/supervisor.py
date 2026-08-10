import operator

from langgraph.graph import END, START, add_messages
from typing_extensions import Annotated

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver

from src.models.game import Move
from src.utils.llms import get_llm
from src.models.workflow import WorkflowSettings
from src.models.workflow import BaseAgent

class SupervisorState(BaseModel):
    """State model for the supervisor agent.

    Attributes:
        messages: Conversation history messages
        game_state: The game_state we exist in
        moves: The previous moves played in the game
    """
    messages: Annotated[list[AnyMessage], add_messages] = Field([], description='The conversation history')
    game_state: dict = Field(default_factory={}, description='The current state of the game')
    moves: list[dict] = Field([], description='The move history')

class SupervisorAgent(BaseAgent):
    def __init__(self, settings=WorkflowSettings()):
        super().__init__(SupervisorState, settings)
        self._build_graph()

    def _build_graph(self):
        self.add_node(self.CONVERSE, self.converse)

        self.add_edge(START, self.CONVERSE)
        self.add_edge(self.CONVERSE, END)

        self.graph = self.compile(checkpointer=MemorySaver())

    CONVERSE = 'converse'
    def converse(self, state: SupervisorState) -> dict:
        prompt = """
            You are an autonomous Kaggriculture farming agent.

            Task
            Analyze the current GameState and determine the optimal next Move.
            Maximize farm wealth and long-term productivity while making efficient use of money, resources, workers, land, time, and market opportunities.

            Rules
            * Use only information available in the current GameState.
            * Never invent actions, resources, prices, workers, or game state.
            * Only select actions that are valid for the current state.
            * Consider both immediate profit and long-term productivity.
            * Use available hired workers when beneficial.
            * Consider market prices before buying or selling.
            * If no useful action is available, the farmer should Pass.
            * Return valid JSON only.
            * Do not return explanations, Markdown, code fences, or additional fields.

            Input
            {game_state}: The current state of the game

            Output (JSON format)
            * farmer: dict (the farmer's next action)
            * hands: list (actions for hired workers)
            * market: list (market actions)
        """

        formatted_prompt = prompt.format(game_state=state.game_state)
        system_message = SystemMessage(content=formatted_prompt)
        llm = get_llm(temperature=self.settings.temperature).with_structured_output(Move)

        response = llm.invoke(
            [system_message] + state.messages
        )

        state.moves.append(response)
        return state

    def invoke(self, query: str, state: SupervisorState):
        """Invoke the agent graph and return the response.
        
        Args:
            state: Initial support state

        Returns:
            Generated response string
        """
        state.messages.append(HumanMessage(query))
        return self.graph.invoke(state, config=self.settings.config)