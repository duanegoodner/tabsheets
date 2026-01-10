from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tabsheets.table_sheet_manager import TableSheetManager


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
