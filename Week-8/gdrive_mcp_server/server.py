#!/usr/bin/env python3
"""
MCP server for Google Drive integration.
This server exposes methods to interact with Google Drive files and folders.
"""

import os
import sys
import json
import io
import argparse
from typing import Any, Optional, List, Dict
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

print("Starting Google Drive MCP server!", file=sys.stderr)

class GoogleDriveClient:
    """Client for interacting with the Google Drive API."""

    def __init__(self):
        """Initialize the Google Drive client using TOKEN_PATH environment variable."""
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        # Get token path from environment variable
        token_path = os.environ.get('TOKEN_PATH', 'token.json')
        self.token_path = Path(token_path)
        self.service = self._get_service()

    def _get_credentials(self) -> Credentials:
        """Get credentials from the saved JSON token file."""
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"Token file not found at {self.token_path}. "
                "Please ensure TOKEN_PATH is set in .env"
            )

        try:
            with open(self.token_path, 'r') as token:
                token_data = json.load(token)
                creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Error loading token JSON file: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed token back to JSON file
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                except RefreshError as e:
                    raise RuntimeError(
                        f"Error refreshing token: {e}. "
                        "Please re-authenticate."
                    )
            else:
                raise RuntimeError(
                    "Invalid or missing credentials. "
                    "Please ensure you have a valid token.json file."
                )

        return creds

    def _get_service(self):
        """Get the Google Drive service instance."""
        try:
            creds = self._get_credentials()
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Error initializing Google Drive service: {e}", file=sys.stderr)
            raise

    def search_files(
        self,
        query: str,
        page_size: int = 10,
        page_token: Optional[str] = None
    ) -> dict:
        """Search for files in Google Drive."""
        try:
            results = self.service.files().list(
                q=f"name contains '{query}'",
                pageSize=page_size,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, webViewLink)"
            ).execute()
            
            return self._format_search_response(results)
        except Exception as e:
            return {"error": str(e)}

    def get_file(self, file_id: str) -> dict:
        """Get file content and metadata."""
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, webViewLink"
            ).execute()
            
            # Get file content
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return {
                "metadata": {
                    "id": file_metadata['id'],
                    "name": file_metadata['name'],
                    "mime_type": file_metadata['mimeType'],
                    "web_view_link": file_metadata['webViewLink']
                },
                "content": fh.getvalue().decode('utf-8')
            }
        except Exception as e:
            return {"error": str(e)}

    def _format_search_response(self, response: dict) -> dict:
        """Format the Google Drive search response."""
        items = response.get('files', [])
        formatted_files = []
        
        for item in items:
            formatted_file = {
                "id": item['id'],
                "name": item['name'],
                "mime_type": item['mimeType'],
                "web_view_link": item['webViewLink']
            }
            formatted_files.append(formatted_file)

        return {
            "files": formatted_files,
            "next_page_token": response.get('nextPageToken')
        }

# Initialize MCP server
mcp = FastMCP("Google Drive MCP Server")

@mcp.tool()
def search_files(query: str, page_size: int = 10) -> dict[str, Any]:
    """Search for files in Google Drive."""
    return drive_client.search_files(query=query, page_size=page_size)

@mcp.tool()
def get_file(file_id: str) -> dict[str, Any]:
    """Get file content and metadata."""
    return drive_client.get_file(file_id=file_id)

def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description='Google Drive MCP Server')
    parser.add_argument('--http', action='store_true', help='Run in HTTP mode')
    args = parser.parse_args()

    # Initialize the drive client (uses TOKEN_PATH from environment)
    global drive_client
    drive_client = GoogleDriveClient()

    if args.http:
        mcp.run(host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main() 