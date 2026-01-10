from __future__ import annotations

import os
import sys
import tomllib
import webbrowser
from functools import cached_property
from pathlib import Path
from typing import List, Optional, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from tabsheets.config_resolver import ConfigResolver
from tabsheets.table_utils import (
    a1_range_for_size,
    extract_csv_table,
    extract_first_pipe_table,
    extract_tsv_table,
    write_csv_table,
    write_markdown_table,
    write_tsv_table,
)

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_MIME = "application/vnd.google-apps.spreadsheet"





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

    @cached_property
    def spreadsheet_id(self) -> str:
        """Find or create the spreadsheet by title in the specified folder."""
        # Try to find existing spreadsheet with this title
        existing = self.find_sheet_in_folder_by_name(
            self.drive_folder_id, self.sheet_title
        )

        if existing:
            # Prompt user for confirmation before overwriting
            print(
                f"\n⚠️  A spreadsheet named '{self.sheet_title}' already exists in this folder."
            )
            print(f"   URL: {existing.get('webViewLink', 'N/A')}")
            response = (
                input("\nDo you want to proceed and overwrite it? (yes/no): ")
                .strip()
                .lower()
            )

            if response in ("yes", "y"):
                print("Proceeding to overwrite the existing spreadsheet...")
                return existing["id"]
            else:
                print(
                    "Operation cancelled. The existing spreadsheet will not be modified."
                )
                sys.exit(0)

        # Create new spreadsheet if not found
        return self._create_spreadsheet()

    def _create_spreadsheet(self) -> str:
        """Create a Google Sheet via Drive API and return spreadsheetId."""
        metadata = {
            "name": self.sheet_title,
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }
        metadata["parents"] = [self.drive_folder_id]  # type: ignore

        created = (
            self.drive.files()  # type: ignore
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
        return created["id"]

    def _extract_table(self) -> List[List[str]]:
        """Extract table from file based on extension."""
        text = self.table_path.read_text(encoding="utf-8")
        suffix = self.table_path.suffix.lower()

        if suffix == ".md":
            return extract_first_pipe_table(text)
        elif suffix == ".csv":
            return extract_csv_table(text)
        elif suffix == ".tsv":
            return extract_tsv_table(text)
        else:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                "Supported formats: .md, .csv, .tsv"
            )

    def clear_and_write(
        self, spreadsheet_id: str, values: List[List[str]]
    ) -> None:
        """
        Clear existing values in a large-enough range, then write values at A1.
        """
        n_rows = len(values)
        n_cols = max((len(r) for r in values), default=0)
        target_range = a1_range_for_size(
            n_rows + 500, n_cols + 10
        )  # pad to clear leftovers

        # Clear
        self.sheets.spreadsheets().values().batchClear(  # type: ignore
            spreadsheetId=spreadsheet_id,
            body={"ranges": [target_range]},
        ).execute()

        # Write
        self.sheets.spreadsheets().values().update(  # type: ignore
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="RAW",
            body={"majorDimension": "ROWS", "values": values},
        ).execute()

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

    def find_sheet_in_folder_by_name(
        self, folder_id: str, name: str, shared_drive_id: str | None = None
    ):
        """Find a spreadsheet in a folder by name."""
        # Escape quotes in the name for the query
        safe_name = name.replace("'", "\\'")
        q = (
            f"'{folder_id}' in parents and trashed = false and "
            f"mimeType = '{SHEET_MIME}' and name = '{safe_name}'"
        )

        params = {
            "q": q,
            "fields": "files(id, name, webViewLink)",
            "pageSize": 10,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }

        if shared_drive_id:
            params.update({"corpora": "drive", "driveId": shared_drive_id})
        else:
            params.update({"corpora": "allDrives"})

        resp = self.drive.files().list(**params).execute()
        files = resp.get("files", [])
        return files[0] if files else None

    # def sync_markdown_to_sheet(self) -> str:
    def sync_table_to_sheet(self) -> str:
        """Main synchronization method: reads table and syncs to Google Sheets.
        Returns the URL of the spreadsheet.
        """
        # Read and parse table
        table = self._extract_table()

        # Update the sheet with the table data
        self.clear_and_write(self.spreadsheet_id, table)

        # Generate URL
        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"

        # Open in browser if requested
        if self.open_browser:
            webbrowser.open(url)

        return url

    def sync_sheet_to_table(self) -> str:
        """Reverse synchronization: reads data from Google Sheets and writes to table file.
        Returns the path of the written table file.
        """
        # Find the spreadsheet (error if not found)
        existing = self.find_sheet_in_folder_by_name(
            self.drive_folder_id, self.sheet_title
        )
        
        if not existing:
            raise ValueError(
                f"No spreadsheet named '{self.sheet_title}' found in the specified folder.\n"
                f"Cannot sync from a non-existent sheet."
            )
        
        sheet_id = existing["id"]
        
        # Check if table file exists and prompt for overwrite
        if self.table_path.exists():
            print(f"\n⚠️  A file already exists at: {self.table_path}")
            response = (
                input("\nDo you want to overwrite it? (yes/no): ")
                .strip()
                .lower()
            )
            
            if response not in ("yes", "y"):
                print("Operation cancelled. The existing file will not be modified.")
                sys.exit(0)
        
        # Read data from the sheet
        result = (
            self.sheets.spreadsheets()  # type: ignore
            .values()
            .get(spreadsheetId=sheet_id, range="A1:ZZ10000")
            .execute()
        )
        
        values = result.get("values", [])
        
        if not values:
            raise ValueError(
                f"No data found in spreadsheet '{self.sheet_title}'. "
                "Cannot write an empty table."
            )
        
        # Determine format and write based on file extension
        suffix = self.table_path.suffix.lower()
        
        if suffix == ".md":
            content = write_markdown_table(values)
        elif suffix == ".csv":
            content = write_csv_table(values)
        elif suffix == ".tsv":
            content = write_tsv_table(values)
        else:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                "Supported formats: .md, .csv, .tsv"
            )
        
        # Write to file
        self.table_path.parent.mkdir(parents=True, exist_ok=True)
        self.table_path.write_text(content, encoding="utf-8")
        
        return str(self.table_path)


        return url
