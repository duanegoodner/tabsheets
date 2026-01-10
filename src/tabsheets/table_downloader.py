from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List

from tabsheets.table_utils import (
    write_csv_table,
    write_markdown_table,
    write_tsv_table,
)

SHEET_MIME = "application/vnd.google-apps.spreadsheet"


class TableDownloader:
    """Handles downloading Google Sheets data to table files."""

    def __init__(
        self,
        drive: Any,
        sheets: Any,
        table_path: Path,
        sheet_title: str,
        drive_folder_id: str,
    ):
        self.drive = drive
        self.sheets = sheets
        self.table_path = table_path
        self.sheet_title = sheet_title
        self.drive_folder_id = drive_folder_id

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

    def read_sheet_data(self, spreadsheet_id: str) -> List[List[str]]:
        """Read all data from a Google Sheet."""
        result = (
            self.sheets.spreadsheets()  # type: ignore
            .values()
            .get(spreadsheetId=spreadsheet_id, range="A1:ZZ10000")
            .execute()
        )

        values = result.get("values", [])

        if not values:
            raise ValueError(
                f"No data found in spreadsheet '{self.sheet_title}'. "
                "Cannot write an empty table."
            )

        return values

    def write_table_file(self, values: List[List[str]]) -> None:
        """Write table data to file based on extension."""
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

    def download(self) -> str:
        """Download Google Sheet data to table file. Returns the file path."""
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
        values = self.read_sheet_data(sheet_id)

        # Write to table file
        self.write_table_file(values)

        return str(self.table_path)
