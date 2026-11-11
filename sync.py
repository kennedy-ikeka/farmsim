import asyncio

from src.utils.config import GOOGLE_RESOURCE_ID, GOOGLE_SHEET_ID
from src.utils.google_drive import GoogleDrive
from src.utils.knowledge import Knowledge

async def sync():
    """Setup the application by syncing Google Drive documents to the Chroma vector store."""

    # docs = Knowledge('farm_docs')
    # await docs.sync_resources(GOOGLE_RESOURCE_ID)

    db = Knowledge('farm_data')
    await db.sync_datasets(GOOGLE_SHEET_ID)

if __name__ == "__main__":
    asyncio.run(sync())