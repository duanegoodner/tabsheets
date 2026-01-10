from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tabsheets.table_sheet_manager import TableSheetManager


def main():
    ap = argparse.ArgumentParser(
        description="Sync tabular data (MD/CSV/TSV) to/from Google Sheets (service account)."
    )
    ap.add_argument(
        "direction",
        choices=["upload", "download"],
        help="Direction of sync: 'upload' (table file -> Google Sheet) or "
        "'download' (Google Sheet -> table file)",
    )
    ap.add_argument(
        "--config",
        type=Path,
        help="Path to TOML configuration file. Optional if all required fields provided via CLI.",
    )
    ap.add_argument(
        "--creds",
        type=Path,
        help="Path to Google service account credentials JSON file. "
        "If not provided, uses TABSHEETS_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS env var.",
    )
    ap.add_argument(
        "--table-path",
        type=Path,
        help="Path to table file (.md, .csv, or .tsv). Overrides/validates against config file.",
    )
    ap.add_argument(
        "--sheet-title",
        type=str,
        help="Title for the Google Spreadsheet. Overrides/validates against config file.",
    )
    ap.add_argument(
        "--drive-folder-id",
        type=str,
        help="Google Drive folder ID where the spreadsheet is located. Overrides/validates against config file.",
    )
    ap.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the spreadsheet in browser after syncing (upload only).",
    )
    args = ap.parse_args()

    # Load from config file if provided, otherwise use CLI args
    if args.config:
        manager = TableSheetManager.from_toml(
            args.config,
            cli_table_path=args.table_path,
            cli_sheet_title=args.sheet_title,
            cli_drive_folder_id=args.drive_folder_id,
            cli_open_browser=args.open_browser,
        )
    else:
        # No config file - use CLI args only
        if not args.table_path or not args.sheet_title or not args.drive_folder_id:
            print(
                "ERROR: When --config is not provided, you must specify: "
                "--table-path, --sheet-title, and --drive-folder-id",
                file=sys.stderr,
            )
            sys.exit(1)
        
        manager = TableSheetManager(
            table_path=args.table_path,
            sheet_title=args.sheet_title,
            drive_folder_id=args.drive_folder_id,
            creds_json=args.creds,
            open_browser=args.open_browser,
        )
    
    if args.creds:
        manager.creds_json = args.creds

    if args.direction == "upload":
        result = manager.sync_table_to_sheet()
    else:  # download
        result = manager.sync_sheet_to_table()
    
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
