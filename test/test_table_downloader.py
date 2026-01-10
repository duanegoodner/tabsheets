"""Tests for TableDownloader."""
import pytest
from datetime import datetime
from pathlib import Path

from tabsheets.sheet_uploader import SheetUploader
from tabsheets.table_downloader import TableDownloader
from tabsheets.table_utils import extract_first_pipe_table, extract_csv_table, extract_tsv_table


class TestTableDownloader:
    """Test table download functionality with real Google Drive."""

    def test_download_to_markdown(
        self, drive_service, sheets_service, sample_md_file, test_folder_id, cleanup, tmp_path
    ):
        """Test downloading a Google Sheet to Markdown file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_MD_Download"
        
        # First, upload a test sheet
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_md_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,
        )
        
        try:
            uploader.upload()
            
            # Now download it
            download_path = tmp_path / "downloaded.md"
            downloader = TableDownloader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
            )
            
            result = downloader.download()
            
            # Verify file was created
            assert download_path.exists()
            assert result == str(download_path)
            
            # Verify content matches
            original = extract_first_pipe_table(sample_md_file.read_text())
            downloaded = extract_first_pipe_table(download_path.read_text())
            assert original == downloaded
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_download_to_csv(
        self, drive_service, sheets_service, sample_csv_file, test_folder_id, cleanup, tmp_path
    ):
        """Test downloading a Google Sheet to CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_CSV_Download"
        
        # Upload first
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_csv_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,
        )
        
        try:
            uploader.upload()
            
            # Download
            download_path = tmp_path / "downloaded.csv"
            downloader = TableDownloader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
            )
            
            result = downloader.download()
            
            assert download_path.exists()
            
            # Verify content
            original = extract_csv_table(sample_csv_file.read_text())
            downloaded = extract_csv_table(download_path.read_text())
            assert original == downloaded
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_download_to_tsv(
        self, drive_service, sheets_service, sample_tsv_file, test_folder_id, cleanup, tmp_path
    ):
        """Test downloading a Google Sheet to TSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_TSV_Download"
        
        # Upload first
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_tsv_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,
        )
        
        try:
            uploader.upload()
            
            # Download
            download_path = tmp_path / "downloaded.tsv"
            downloader = TableDownloader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
            )
            
            result = downloader.download()
            
            assert download_path.exists()
            
            # Verify content
            original = extract_tsv_table(sample_tsv_file.read_text())
            downloaded = extract_tsv_table(download_path.read_text())
            assert original == downloaded
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_download_nonexistent_sheet_raises_error(
        self, drive_service, sheets_service, test_folder_id, tmp_path
    ):
        """Test that downloading non-existent sheet raises error."""
        download_path = tmp_path / "nonexistent.md"
        downloader = TableDownloader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=download_path,
            sheet_title="NONEXISTENT_SHEET",
            drive_folder_id=test_folder_id,
        )
        
        with pytest.raises(ValueError, match="found in the specified folder"):
            downloader.download()

    def test_download_unsupported_format_raises_error(
        self, drive_service, sheets_service, sample_md_file, test_folder_id, cleanup, tmp_path
    ):
        """Test that unsupported file format raises error."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_Invalid_Format"
        
        # Upload a test sheet first
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=sample_md_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,
        )
        
        try:
            uploader.upload()
            
            # Try to download to unsupported format
            download_path = tmp_path / "test.txt"
            downloader = TableDownloader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
            )
            
            with pytest.raises(ValueError, match="Unsupported file format"):
                downloader.download()
                
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)
