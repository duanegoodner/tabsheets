from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any, List

from tabsheets.table_utils import (
    a1_range_for_size,
    extract_csv_table,
    extract_first_pipe_table,
    extract_tsv_table,
)

SHEET_MIME = "application/vnd.google-apps.spreadsheet"


class SheetUploader:
    """Handles uploading table data to Google Sheets."""

    def __init__(
        self,
        drive: Any,
        sheets: Any,
        table_path: Path,
        sheet_title: str,
        drive_folder_id: str,
        open_browser: bool = False,
        skip_prompt: bool = False,
    ):
        self.drive = drive
        self.sheets = sheets
        self.table_path = table_path
        self.sheet_title = sheet_title
        self.drive_folder_id = drive_folder_id
        self.open_browser = open_browser
        self.skip_prompt = skip_prompt
        self.spreadsheet_id: str | None = None  # Track created/used spreadsheet ID

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

    def get_or_create_spreadsheet_id(self) -> str:
        """Find or create the spreadsheet by title in the specified folder."""
        # Try to find existing spreadsheet with this title
        existing = self.find_sheet_in_folder_by_name(
            self.drive_folder_id, self.sheet_title
        )

        if existing:
            if self.skip_prompt:
                # In test mode, just overwrite without prompting
                return existing["id"]
            
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

    def extract_table(self) -> List[List[str]]:
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
        """Clear existing values in a large-enough range, then write values at A1."""
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

    def upload(self) -> str:
        """Upload table data to Google Sheets. Returns the spreadsheet URL."""
        # Read and parse table
        table = self.extract_table()

        # Get or create spreadsheet
        spreadsheet_id = self.get_or_create_spreadsheet_id()
        self.spreadsheet_id = spreadsheet_id  # Track for cleanup

        # Update the sheet with the table data
        self.clear_and_write(spreadsheet_id, table)

        # Generate URL
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        # Open in browser if requested
        if self.open_browser:
            webbrowser.open(url)

        return url
