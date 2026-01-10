from __future__ import annotations

import os
import tomllib
from functools import cached_property
from pathlib import Path
from typing import Optional, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from tabsheets.config_resolver import ConfigResolver
from tabsheets.sheet_uploader import SheetUploader
from tabsheets.table_downloader import TableDownloader

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]





class TableSheetManager:
    """Manages synchronization of tabular data (MD/CSV/TSV) to Google Sheets."""

    def __init__(
        self,
        table_path: Path,
        sheet_title: str,
        drive_folder_id: str,
        creds_json: Optional[Path] = None,
        open_browser: bool = False,
    ):
        self.table_path = table_path
        self.creds_json = creds_json
        self.sheet_title = sheet_title
        self.drive_folder_id = drive_folder_id
        self.open_browser = open_browser

    @classmethod
    def from_toml(
        cls,
        config_path: Path,
        cli_table_path: Optional[Path] = None,
        cli_sheet_title: Optional[str] = None,
        cli_drive_folder_id: Optional[str] = None,
        cli_open_browser: bool = False,
    ) -> "TableSheetManager":
        """Create a TableSheetManager from a TOML configuration file.

        Expected TOML structure:
        [table_sheet_manager]
        table_path = "path/to/table.md"
        sheet_title = "My Sheet Title"
        drive_folder_id = "folder_id"  # required
        open_browser = false  # optional

        CLI arguments can override/validate config values. If both CLI and config
        provide a value, they must match or an error is raised.
        """
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Get the table_sheet_manager section
        section = config.get("table_sheet_manager", {})
        
        # Create resolver to handle CLI/config merging and validation
        resolver = ConfigResolver(section)

        # Resolve required fields
        table_path = resolver.resolve("table_path", cli_table_path, is_path=True)
        sheet_title = resolver.resolve("sheet_title", cli_sheet_title)
        drive_folder_id = resolver.resolve("drive_folder_id", cli_drive_folder_id)

        # Convert to Path if string
        if isinstance(table_path, str):
            table_path = Path(table_path)

        # Resolve optional field (open_browser)
        # CLI flag takes precedence if set to True
        open_browser = cli_open_browser or section.get("open_browser", False)

        return cls(
            table_path=table_path,
            sheet_title=sheet_title,
            drive_folder_id=drive_folder_id,
            creds_json=None,  # Set via CLI argument
            open_browser=open_browser,
        )

    @cached_property
    def _credentials(self) -> service_account.Credentials:
        """Lazy-load service account credentials.

        Tries in order:
        1. creds_json path from CLI --creds argument
        2. TABSHEETS_CREDENTIALS environment variable
        3. GOOGLE_APPLICATION_CREDENTIALS environment variable
        4. Raises error if none available
        """
        creds_path = None

        if self.creds_json:
            creds_path = str(self.creds_json)
        elif "TABSHEETS_CREDENTIALS" in os.environ:
            creds_path = os.environ["TABSHEETS_CREDENTIALS"]
        elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        else:
            raise ValueError(
                "No credentials found. Please use one of:\n"
                "  1. Pass --creds /path/to/credentials.json at the command line\n"
                "  2. Set TABSHEETS_CREDENTIALS environment variable\n"
                "  3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
                "\n"
                "Example:\n"
                "  export TABSHEETS_CREDENTIALS=~/.config/gcloud/my-service-account.json"
            )

        return service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=DRIVE_SCOPES + SHEETS_SCOPES,
        )

    @cached_property
    def drive(self) -> Any:
        """Lazy-load Google Drive API service."""
        return build("drive", "v3", credentials=self._credentials)

    @cached_property
    def sheets(self) -> Any:
        """Lazy-load Google Sheets API service."""
        return build("sheets", "v4", credentials=self._credentials)

    def list_files_in_folder(
        self, folder_id: str, shared_drive_id: str | None = None
    ):
        """List files in a Drive folder."""
        q = f"'{folder_id}' in parents and trashed = false"
        params = {
            "q": q,
            "fields": "files(id, name, mimeType, modifiedTime, webViewLink)",
            "pageSize": 100,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }

        # If the folder is in a Shared Drive and you know the Shared Drive ID,
        # restricting corpora improves reliability and performance.
        if shared_drive_id:
            params.update(
                {
                    "corpora": "drive",
                    "driveId": shared_drive_id,
                }
            )
        else:
            # Otherwise you can search across everything you have access to.
            params.update(
                {
                    "corpora": "allDrives",
                }
            )

        resp = self.drive.files().list(**params).execute()  # type: ignore
        return resp.get("files", [])

    def sync_table_to_sheet(self) -> str:
        """Upload table data to Google Sheets. Returns the spreadsheet URL."""
        uploader = SheetUploader(
            drive=self.drive,
            sheets=self.sheets,
            table_path=self.table_path,
            sheet_title=self.sheet_title,
            drive_folder_id=self.drive_folder_id,
            open_browser=self.open_browser,
        )
        return uploader.upload()

    def sync_sheet_to_table(self) -> str:
        """Download Google Sheet data to table file. Returns the file path."""
        downloader = TableDownloader(
            drive=self.drive,
            sheets=self.sheets,
            table_path=self.table_path,
            sheet_title=self.sheet_title,
            drive_folder_id=self.drive_folder_id,
        )
        return downloader.download()
