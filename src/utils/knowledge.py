from typing import Optional

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from chromadb.config import Settings
import chromadb
from langchain_core.tools import StructuredTool
import pandas as pd
from os import path, makedirs

from src.utils.splitter import split_dataframe, split_text
from src.utils.config import OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL, VECTOR_DIR, DATA_DIR
from src.utils.logger import get_logger
from src.utils.tool_set import AgentTool
from src.utils.google_drive import GoogleDrive

logger = get_logger('Knowledge')
drive = GoogleDrive()

class Knowledge:
    """Manages vector storage for RAG-based knowledge retrieval.

    Handles ingestion, updating, and retrieval of documents from
    Chroma vector store. Supports syncing from Google Drive and
    ingesting from pandas DataFrames.
    """

    def __init__(self, collection_name: str = 'finsight', persistent_dir: str = VECTOR_DIR):
        """Initialize the knowledge manager with Chroma vector store.

        Args:
            drive: Instance of GoogleDrive for document management
            collection_name: Name of the Chroma collection
            persistent_dir: Directory path for persistent storage
        """
        self.collection_name = collection_name
        self.embedding = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
        self.persistent_dir = persistent_dir

        self.client = chromadb.PersistentClient(
            path=self.persistent_dir,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self.store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding,
            persist_directory=self.persistent_dir,
            client=self.client
        )

    def ingest_from_text(self, text: str, file_id: str, metadata: dict = {}):
        """Ingest text into the vector store.

        Args:
            text: Text to ingest
            metadata: Metadata for the text
            file_id: Identifier for the text source
        """
        chunks = split_text(text)
        self.update_document(chunks, file_id, metadata)
        logger.info(f"Ingested text with id {file_id} into vector store")

    def ingest_from_dataframe(self, df: pd.DataFrame, file_id: str, metadata: dict = {}):
        """Ingest data from a pandas DataFrame into the vector store.

        Args:
            df: DataFrame containing data to ingest
            file_id: Identifier for the data source
        """
        documents = split_dataframe(df)
        chunks = split_text("\n".join([doc.page_content for doc in documents]))
        self.update_document(chunks, file_id, metadata)
        logger.info(f"Ingested dataframe with id {file_id} into vector store")

    def get_file(self, file_id: str):
        """Retrieve all chunks associated with a file ID.

        Args:
            file_id: File identifier to search for

        Returns:
            Dictionary with ids, metadatas, and documents
        """
        results = self.collection.get(
            where={"file_id": {"$eq": file_id}}
        )
        return results

    def delete_document(self, file_id: str):
        """Delete all chunks associated with a file ID.

        Args:
            file_id: File identifier to delete
        """
        results = self.get_file(file_id)
        if results['ids']:
            self.collection.delete(ids=results['ids'])

        logger.info(f"Deleted document with id {file_id} from vector store")

    def update_document(self, chunks: list, file_id: str, metadata: dict = {}):
        """Download and ingest a document from Google Drive.

        Deletes any existing version before adding the updated content.

        Args:
            file_id: Google Drive file ID
        """
        self.delete_document(file_id)
        self.store.add_texts(
            texts=chunks,
            metadatas=[{**metadata, "file_id": file_id}] * len(chunks),
            ids=[f"{file_id}_{i}" for i in range(len(chunks))]
        )

    async def list_outdated_documents(self, folder_id: str) -> list:
        """Find documents in Drive that are newer than stored versions.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of file IDs that need updating
        """
        docs = drive.list_documents(folder_id)
        outdated_docs = []

        for doc in docs:
            file_id = doc['id']
            modifiedTime = doc['modifiedTime']

            stored_doc = self.collection.get(where={"file_id": {"$eq": file_id}})
            if not stored_doc['ids']:
                outdated_docs.append(file_id)
                continue

            metadatas = stored_doc['metadatas']
            if metadatas is None:
                return outdated_docs

            stored_modefied_time = metadatas[0]['modifiedTime']
            if modifiedTime > stored_modefied_time:
                outdated_docs.append(file_id)

        return outdated_docs

    async def sync_resources(self, folder_id: str):
        """Sync outdated documents from Google Drive to vector store.

        Args:
            folder_id: Google Drive folder ID
        """
        files = await self.list_outdated_documents(folder_id)
        logger.info(f"Found {len(files)} outdated files in folder {folder_id}")

        for file in files:
            text, metadata = await drive.download(file.id)
            chunks = split_text(text)
            self.update_document(chunks, file['id'], metadata)
            logger.info(f"Ingested file {file['name']} with id {file['id']} into vector store")

    async def sync_datasets(self, sheet_id: str, datasets: Optional[list[str]] = None) -> list[str]:
        """Sync local dataset CSV files from the datasets folder into the knowledge base.

        Reads every CSV file in the configured datasets directory, converts them into
        text chunks, and stores them in the vector store keyed by filename. Existing
        entries for the same file are replaced so the knowledge base stays up to date.

        Args:
            sheet_id: Google Sheet ID containing dataset information
            datasets: List of dataset file paths to sync

        Returns:
            List of synced file paths.
        """
        makedirs(DATA_DIR, exist_ok=True)
        synced: list[str] = []

        datasets = datasets if datasets else await drive.download_sheet(sheet_id)
        for filepath in datasets:
            if not path.isfile(filepath):
                logger.warning(f"Dataset file not found: {filepath}")
                continue

            try:
                df = pd.read_csv(filepath)
            except Exception as exc:
                logger.error(f"Failed to read dataset {filepath}: {exc}")
                continue

            file_id = path.basename(filepath)
            self.ingest_from_dataframe(df, file_id)
            synced.append(filepath)
            logger.info(f"Synced dataset {file_id} into vector store")

        return synced

    def retrieve(self, query: str, search_count: int = 3) -> list:
        """Retrieve relevant documents from the vector store.

        Uses MMR (Maximum Marginal Relevance) search for diversity.

        Args:
            query: Search query string
            search_count: Number of results to return

        Returns:
            List of relevant Document objects
        """
        logger.info(f"Looking for documents")
        retriever = self.store.as_retriever(search_type='mmr', search_kwargs={'k': search_count})
        data = retriever.invoke(query)
        return data

    def retrieve_tool(self, name: str, description: str) -> AgentTool:
        """Create a LangChain tool for knowledge retrieval.

        Returns:
            AgentTool for querying the vector store
        """
        tool = StructuredTool.from_function(
            name=name,
            description=description,
            func=lambda query, search_count=3: self.retrieve(query=query, search_count=search_count)
        )

        return AgentTool(action='Learning', tool=tool)
    