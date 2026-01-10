#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tomllib
import webbrowser
from functools import cached_property
from pathlib import Path
from typing import List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build


DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_MIME = "application/vnd.google-apps.spreadsheet"


SEP_RE = re.compile(r"^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|$")


def extract_first_pipe_table(md_text: str) -> List[List[str]]:
    """
    Extract the first Markdown pipe table (rows beginning and ending with '|').
    Assumes:
      - One logical pipe table
      - No multiline cells
      - Pipes '|' are used only as delimiters (not inside cell text)
    """
    lines = md_text.splitlines()
    table_lines: List[str] = []
    in_table = False

    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            in_table = True
            table_lines.append(s)
        else:
            if in_table:
                break

    if not table_lines:
        raise ValueError(
            "No Markdown pipe table found (lines that start and end with '|')."
        )

    rows: List[List[str]] = []
    for ln in table_lines:
        if SEP_RE.match(ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(cells)

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def extract_csv_table(csv_text: str) -> List[List[str]]:
    """Extract table from CSV text."""
    reader = csv.reader(csv_text.splitlines())
    rows = [list(row) for row in reader]

    if not rows:
        raise ValueError("No data found in CSV file.")

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def extract_tsv_table(tsv_text: str) -> List[List[str]]:
    """Extract table from TSV (tab-separated values) text."""
    reader = csv.reader(tsv_text.splitlines(), delimiter="\t")
    rows = [list(row) for row in reader]

    if not rows:
        raise ValueError("No data found in TSV file.")

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def a1_range_for_size(n_rows: int, n_cols: int) -> str:
    """Return an A1 range covering the given rows/cols, e.g. A1:AB123."""

    def col_to_a1(col_idx_0: int) -> str:
        # 0 -> A, 25 -> Z, 26 -> AA
        col = col_idx_0 + 1
        s = ""
        while col:
            col, rem = divmod(col - 1, 26)
            s = chr(65 + rem) + s
        return s

    end_col = col_to_a1(max(0, n_cols - 1))
    end_row = max(1, n_rows)
    return f"A1:{end_col}{end_row}"


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
    def from_toml(cls, config_path: Path) -> "TableSheetManager":
        """Create a TableSheetManager from a TOML configuration file.
        
        Expected TOML structure:
        [table_sheet_manager]
        table_path = "path/to/table.md"
        sheet_title = "My Sheet Title"
        drive_folder_id = "folder_id"  # required
        open_browser = false  # optional
        
        Note: Credentials must be provided via --creds CLI argument.
        """
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        
        # Get the table_sheet_manager section
        section = config.get("table_sheet_manager", {})
        
        # Required fields
        table_path = Path(section["table_path"])
        sheet_title = section["sheet_title"]
        drive_folder_id = section["drive_folder_id"]
        
        # Optional fields with defaults
        open_browser = section.get("open_browser", False)
        
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
        1. creds_json path from config
        2. GOOGLE_APPLICATION_CREDENTIALS environment variable
        3. Raises error if neither is available
        """
        creds_path = None
        
        if self.creds_json:
            creds_path = str(self.creds_json)
        elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        else:
            raise ValueError(
                "No credentials found. Please either:\n"
                "  1. Set 'creds_json' in your config.toml, or\n"
                "  2. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
                "\n"
                "Recommended: Store credentials in ~/.config/gcloud/ and use:\n"
                "  export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/my-service-account.json"
            )
        
        return service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=DRIVE_SCOPES + SHEETS_SCOPES,
        )

    @cached_property
    def drive(self) -> Resource:
        """Lazy-load Google Drive API service."""
        return build("drive", "v3", credentials=self._credentials)

    @cached_property
    def sheets(self) -> Resource:
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
            print(f"\n⚠️  A spreadsheet named '{self.sheet_title}' already exists in this folder.")
            print(f"   URL: {existing.get('webViewLink', 'N/A')}")
            response = input("\nDo you want to proceed and overwrite it? (yes/no): ").strip().lower()
            
            if response in ('yes', 'y'):
                print("Proceeding to overwrite the existing spreadsheet...")
                return existing["id"]
            else:
                print("Operation cancelled. The existing spreadsheet will not be modified.")
                sys.exit(0)
        
        # Create new spreadsheet if not found
        return self._create_spreadsheet()

    def _create_spreadsheet(self) -> str:
        """Create a Google Sheet via Drive API and return spreadsheetId."""
        metadata = {
            "name": self.sheet_title,
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }
        metadata["parents"] = [self.drive_folder_id]

        created = (
            self.drive.files()
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
        self.sheets.spreadsheets().values().batchClear(
            spreadsheetId=spreadsheet_id,
            body={"ranges": [target_range]},
        ).execute()

        # Write
        self.sheets.spreadsheets().values().update(
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

        resp = self.drive.files().list(**params).execute()
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


def main():
    ap = argparse.ArgumentParser(
        description="Sync tabular data (MD/CSV/TSV) to Google Sheets (service account)."
    )
    ap.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to TOML configuration file",
    )
    ap.add_argument(
        "--creds",
        required=True,
        type=Path,
        help="Path to Google service account credentials JSON file. "
        "Falls back to GOOGLE_APPLICATION_CREDENTIALS env var if file not found.",
    )
    args = ap.parse_args()

    manager = TableSheetManager.from_toml(args.config)
    manager.creds_json = args.creds
    
    url = manager.sync_table_to_sheet()
    print(url)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
