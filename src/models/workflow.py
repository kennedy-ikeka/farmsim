from typing import Optional
from uuid import uuid4
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field, computed_field
from langchain_core.tools import StructuredTool

from src.utils.logger import get_logger


class AgentToolState(BaseModel):
    """Represents a tool available to an AI agent.

    Attributes:
        tool: The LangChain StructuredTool instance
        action: Optional action identifier for the tool
    """

    tool: StructuredTool
    action: Optional[str]

class WorkflowSettings(BaseModel):
    """Settings for AI workflow execution.

    Attributes:
        session_id: Unique identifier for the workflow session
        temperature: LLM temperature setting for response generation
    """
    session_id: str = Field(uuid4().hex, description='The session id of the workflow')
    temperature: float = Field(0, description='The temperature of the workflow')
    online: bool = Field(True, description='Whether the workflow is online or offline')

    @computed_field
    @property
    def config(self) -> dict:
        """Generate LangGraph configuration dictionary with thread ID.

        Returns:
            Configuration dict for LangGraph thread management
        """
        return {'configurable': {'thread_id': self.session_id}}


class BaseWorkflow(StateGraph):
    """Base class for AI workflows using LangGraph.

    Provides common workflow functionality for AI agent implementations.
    """

    def __init__(self, state_schema: type, settings = WorkflowSettings()) -> None:
        """Initialize the workflow with state schema and settings.

        Args:
            state_schema: Pydantic model defining workflow state
            settings: Workflow configuration settings
        """
        super().__init__(state_schema)
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)

    def invoke(self, state):
        """Invoke the workflow with given state.

        Args:
            state: Current workflow state
        """
        self.logger.info('Invoked')


class BaseAgent(BaseWorkflow):
    """Base class for AI agents.

    Extends BaseWorkflow with streaming capabilities for responses.
    """

    def __init__(self, state_schema: type, settings = WorkflowSettings()) -> None:
        """Initialize the agent with state schema and settings.

        Args:
            state_schema: Pydantic model defining agent state
            settings: Agent configuration settings
        """
        super().__init__(state_schema)
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)

    def stream(self, state, db, cache):
        """Stream responses from the agent.

        Args:
            state: Current agent state
            db: Database connection
            cache: Cache connection
        """
        ...