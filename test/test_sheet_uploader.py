"""Tests for SheetUploader."""
import pytest
from datetime import datetime
from pathlib import Path

from tabsheets.sheet_uploader import SheetUploader


class TestSheetUploader:
    """Test sheet upload functionality with real Google Drive."""

    def test_upload_markdown_table(
        self, drive_service, sheets_service, sample_md_file, test_folder_id, cleanup
    ):
        """Test uploading a Markdown table to Google Sheets."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_MD_Upload"
        
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_md_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,  # Skip user confirmation in tests
        )
        
        try:
            url = uploader.upload()
            
            # Verify URL is returned
            assert "https://docs.google.com/spreadsheets/d/" in url
            assert "/edit" in url
            
            # Verify spreadsheet ID is tracked
            assert uploader.spreadsheet_id is not None
            
            # Verify sheet was created
            found = uploader.find_sheet_in_folder_by_name(test_folder_id, sheet_title)
            assert found is not None
            assert found["name"] == sheet_title
            
        finally:
            # Cleanup using tracked spreadsheet_id
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_upload_csv_table(
        self, drive_service, sheets_service, sample_csv_file, test_folder_id, cleanup
    ):
        """Test uploading a CSV table to Google Sheets."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_CSV_Upload"
        
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_csv_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,  # Skip user confirmation in tests
        )
        
        try:
            url = uploader.upload()
            assert "https://docs.google.com/spreadsheets/d/" in url
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_upload_tsv_table(
        self, drive_service, sheets_service, sample_tsv_file, test_folder_id, cleanup
    ):
        """Test uploading a TSV table to Google Sheets."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_TSV_Upload"
        
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_tsv_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,  # Skip user confirmation in tests
        )
        
        try:
            url = uploader.upload()
            assert "https://docs.google.com/spreadsheets/d/" in url
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_extract_table_unsupported_format_raises_error(
        self, drive_service, sheets_service, tmp_path, test_folder_id
    ):
        """Test that unsupported file format raises error."""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("some text")
        
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=invalid_file,
            sheet_title="TEST_Invalid",
            drive_folder_id=test_folder_id,
            open_browser=False,
        )
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            uploader.extract_table()
