from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils.config import DATA_DIR, GOOGLE_APPLICATION_CREDENTIALS
from src.utils.storage import Storage
from src.utils.logger import get_logger

logger = get_logger('GoogleDrive')
storage = Storage()

class GoogleDrive:
    """Google Drive integration for document listing and downloading.

    Uses Google API client with service account authentication to
    access Drive files and Google Docs editor files.
    """


    def document_service(self):
        """Create Google Docs API service client.

        Returns:
            Authenticated Google Docs API service instance
        """
        scopes = ['https://www.googleapis.com/auth/documents.readonly']
        creds = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes)
        return build('docs', 'v1', credentials=creds, cache_discovery=False)

    def service(self, asset_type: str = 'drive', version: str = 'v3'):
        """Create Google Drive API service client.

        Returns:
            Authenticated Google Drive API service instance
        """
        scopes = [
            'https://www.googleapis.com/auth/drive.metadata.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/spreadsheets.readonly'
        ]
        creds = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes)
        return build(asset_type, version, credentials=creds, cache_discovery=False)

    def list_documents(self, folder_id: str) -> list:
        """List all documents in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of file metadata dictionaries
        """
        service = self.service()
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, fields='nextPageToken, files(id, name, mimeType, modifiedTime)').execute()
        return response['files']

    async def download(self, file_id: str, as_binary: bool = False):
        """Download a file from Google Drive.

        Handles Google Docs editor files by exporting them to native
        formats (PDF for Docs/Slides, XLSX for Sheets).

        Args:
            file_id: Google Drive file ID
            as_binary: Whether to return binary data instead of text

        Returns:
            Tuple of (text content, file metadata)
        """
        service = self.service()
        metadata = service.files().get(fileId=file_id, fields='name, mimeType, modifiedTime').execute()
        original_mime_type = metadata['mimeType']

        if original_mime_type == 'application/vnd.google-apps.document':
            request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
            metadata['mimeType'] = 'application/pdf'
        elif original_mime_type == 'application/vnd.google-apps.spreadsheet':
            request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            metadata['mimeType'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif original_mime_type == 'application/vnd.google-apps.presentation':
            request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
            metadata['mimeType'] = 'application/pdf'
        else:
            request = service.files().get_media(fileId=file_id)

        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            chunk = downloader.next_chunk()
            status, done = chunk
            if status:
                logger.info(f"[Drive Download] {int(status.progress() * 100)}%")

        file_stream.seek(0)
        data = file_stream.read()
        if not as_binary:
            data = storage.binary_to_text(data, metadata['name'], metadata['mimeType'])

        return {
            'metadata': metadata,
            'data': data
        }

    def download_multiple(self, files: list[str], max_workers: int = 5) -> dict:
        """Download multiple files concurrently using thread pool.

        Args:
            files: List of Google Drive file IDs
            max_workers: Maximum number of concurrent downloads

        Returns:
            Dictionary mapping file IDs to text and metadata
        """
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(self.download, fid): fid for fid in files}

            for future in as_completed(future_to_file):
                file_id = future_to_file[future]
                try:
                    result = future.result()
                    results[file_id] = result
                except Exception as e:
                    logger.error(f"Failed to download {file_id}: {e}")
        return results

    async def download_sheet(self, sheet_id: str) -> list[str]:
        """Download every Google Sheet in a folder as a CSV file.

        Uses the existing ``download`` method to fetch the spreadsheet as an
        XLSX workbook, then converts each sheet to a CSV and stores it in the
        datasets folder using ``storage.upload``.

        Args:
            sheet_id: Google Drive file ID of the spreadsheet.

        Returns:
            List of file paths for the saved CSV files.
        """

        s = self.service('sheets', 'v4')
        path_list = []
        meta = s.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_tables = [s["properties"]["title"] for s in meta["sheets"]]

        for table in sheet_tables:
            logger.info(f"Downloading sheet table '{table}' from spreadsheet ID {sheet_id}")
            values = s.spreadsheets().values().get(spreadsheetId=sheet_id, range=table).execute()

            df = pd.DataFrame(values.get('values', []))
            path = f"{DATA_DIR}/{table}.csv"
            df.to_csv(path, index=False)
            path_list.append(path)

        return path_list