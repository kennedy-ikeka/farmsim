from langgraph.graph import END
from langchain_core.tools import StructuredTool
from typing_extensions import Optional
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from src.utils.librarian import Librarian
from src.models.workflow import AgentToolState, BaseWorkflow, WorkflowSettings
from langchain_core.tools import StructuredTool


class InformantState(BaseModel):
    """State model for search workflow.

    Attributes:
        query: User's search query
        documents: Retrieved documents
        search_count: Number of documents to retrieve
    """
    query: str = Field(..., description='The query of the user')
    documents: list[Document] = Field(default_factory=list, description='The retreived documents')
    search_count: int = Field(5, description='The number of documents to retreive')


class InformantWorkflow(BaseWorkflow):
    """Workflow for searching documents from vector store or web.

    Supports both local knowledge base search and web search via Tavily.
    Includes document ranking based on relevance.
    """

    def __init__(self, collection_names: list[str] = [], settings=WorkflowSettings(), benchmark: float = 0):
        """Initialize the search workflow.

        Args:
            drive: The drive containing the vector store
            collection_names: List of vector store collection names
            settings: Workflow configuration settings
            benchmark: Minimum relevance threshold for documents
        """
        super().__init__(InformantState, settings=settings)
        self._build_graph()

        self.librarians = [Librarian(collection_name=name) for name in collection_names]
        self.settings.online = settings.online or bool(not len(collection_names))
        self.benchmark = benchmark

    def _build_graph(self):
        """Build the workflow graph with retrieve, rank, and web search nodes."""
        self.add_node(self.RETRIEVE, self.retreive)

        self.set_entry_point(self.RETRIEVE)
        self.add_edge(self.RETRIEVE, END)

        self.graph = self.compile()

    RETRIEVE = 'retreive'
    def retreive(self, state: InformantState) -> dict:
        """Retrieve documents from knowledge base.

        Args:
            state: Current workflow state with query

        Returns:
            Dictionary with retrieved documents
        """
        retrieved_docs = []

        for lib in self.librarians:
            docs = lib.retrieve(state.query, state.search_count)
            retrieved_docs.extend(docs)

        self.logger.info('Retrieved Documents')
        return {'documents': retrieved_docs}

    def invoke(self, state: InformantState) -> list[Document]:
        """Execute the workflow and return documents.

        Args:
            state: Initial search state

        Returns:
            List of retrieved and ranked documents
        """
        super().invoke(state)
        response = self.graph.invoke(state)
        self.logger.info('Invoked!')
        return response['documents']

    def as_tool(self, name: str) -> AgentToolState:
        """Convert workflow into a LangChain tool.

        Args:
            name: Tool name

        Returns:
            AgentTool wrapping the workflow
        """
        tool = StructuredTool.from_function(
            name=name,
            description=(
                "Retrieve game details from the Kaggriculture knowledge base. Use "
                "this to look up rules, mechanics, crop and animal stats, market "
                "behavior, building costs, and any other in-game facts that should "
                "inform a decision."
            ),
            func=lambda query, search_count=5: self.invoke(
                InformantState(query=query, search_count=search_count)
            )
        )

        return AgentToolState(action='Informing', tool=tool)
