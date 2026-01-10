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
        required=True,
        type=Path,
        help="Path to TOML configuration file",
    )
    ap.add_argument(
        "--creds",
        type=Path,
        help="Path to Google service account credentials JSON file. "
        "If not provided, uses TABSHEETS_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS env var.",
    )
    args = ap.parse_args()

    manager = TableSheetManager.from_toml(args.config)
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
