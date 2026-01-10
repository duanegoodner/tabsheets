"""Pytest configuration and shared fixtures."""
import os
import pytest
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from drive_cleanup import DriveCleanup


DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


@pytest.fixture(scope="session")
def credentials():
    """Get Google service account credentials from environment variable."""
    creds_path = os.environ.get("TABSHEETS_CREDENTIALS")
    if not creds_path:
        pytest.skip(
            "TABSHEETS_CREDENTIALS environment variable not set. "
            "Set it to run integration tests."
        )
    
    return service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=DRIVE_SCOPES + SHEETS_SCOPES,
    )


@pytest.fixture(scope="session")
def test_folder_id():
    """Get test Google Drive folder ID from environment variable."""
    folder_id = os.environ.get("TABSHEETS_TEST_FOLDER_ID")
    if not folder_id:
        pytest.skip(
            "TABSHEETS_TEST_FOLDER_ID environment variable not set. "
            "Set it to run integration tests."
        )
    return folder_id


@pytest.fixture(scope="session")
def drive_service(credentials):
    """Create Google Drive API service."""
    return build("drive", "v3", credentials=credentials)


@pytest.fixture(scope="session")
def sheets_service(credentials):
    """Create Google Sheets API service."""
    return build("sheets", "v4", credentials=credentials)


@pytest.fixture
def cleanup(drive_service):
    """Provide cleanup utility for tests."""
    return DriveCleanup(drive_service)


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_md_file(tmp_path_factory):
    """Create a temporary sample Markdown table file."""
    tmp_dir = tmp_path_factory.mktemp("data")
    md_file = tmp_dir / "sample.md"
    md_file.write_text(
        "| Name    | Age | City        |\n"
        "|---------|-----|-------------|\n"
        "| Alice   | 30  | New York    |\n"
        "| Bob     | 25  | Los Angeles |\n"
        "| Charlie | 35  | Chicago     |\n"
    )
    return md_file


@pytest.fixture(scope="session")
def sample_csv_file(tmp_path_factory):
    """Create a temporary sample CSV file."""
    tmp_dir = tmp_path_factory.mktemp("data")
    csv_file = tmp_dir / "sample.csv"
    csv_file.write_text(
        "Name,Age,City\n"
        "Alice,30,New York\n"
        "Bob,25,Los Angeles\n"
        "Charlie,35,Chicago\n"
    )
    return csv_file


@pytest.fixture(scope="session")
def sample_tsv_file(tmp_path_factory):
    """Create a temporary sample TSV file."""
    tmp_dir = tmp_path_factory.mktemp("data")
    tsv_file = tmp_dir / "sample.tsv"
    tsv_file.write_text(
        "Name\tAge\tCity\n"
        "Alice\t30\tNew York\n"
        "Bob\t25\tLos Angeles\n"
        "Charlie\t35\tChicago\n"
    )
    return tsv_file
