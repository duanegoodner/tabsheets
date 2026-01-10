"""Tests for TableSheetManager."""
import pytest
from datetime import datetime
from pathlib import Path

from tabsheets.table_sheet_manager import TableSheetManager
from tabsheets.table_utils import extract_first_pipe_table


class TestTableSheetManager:
    """Test end-to-end table/sheet management."""

    def test_from_toml(self, tmp_path):
        """Test creating manager from TOML config."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[table_sheet_manager]
table_path = "/path/to/table.md"
sheet_title = "Test Sheet"
drive_folder_id = "test123"
open_browser = false
""")
        
        manager = TableSheetManager.from_toml(config_file)
        
        assert manager.table_path == Path("/path/to/table.md")
        assert manager.sheet_title == "Test Sheet"
        assert manager.drive_folder_id == "test123"
        assert manager.open_browser is False

    def test_from_toml_with_cli_override(self, tmp_path):
        """Test creating manager with CLI overrides."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[table_sheet_manager]
table_path = "/path/to/table.md"
sheet_title = "Test Sheet"
drive_folder_id = "test123"
""")
        
        manager = TableSheetManager.from_toml(
            config_file,
            cli_table_path=Path("/path/to/table.md"),  # Same as config
            cli_sheet_title="Test Sheet",
        )
        
        assert manager.sheet_title == "Test Sheet"

    def test_from_toml_cli_conflict_raises_error(self, tmp_path):
        """Test that CLI/config conflicts raise error."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[table_sheet_manager]
sheet_title = "Config Title"
drive_folder_id = "test123"
table_path = "/path/to/table.md"
""")
        
        with pytest.raises(ValueError, match="Conflict"):
            TableSheetManager.from_toml(
                config_file,
                cli_sheet_title="Different Title"
            )

    def test_sync_table_to_sheet_integration(
        self, drive_service, sheets_service, sample_md_file, test_folder_id, cleanup, tmp_path
    ):
        """Test full upload workflow."""
        # Set credentials via environment for this test
        import os
        creds_path = os.environ.get("TABSHEETS_CREDENTIALS")
        if not creds_path:
            pytest.skip("TABSHEETS_CREDENTIALS not set")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_Manager_Upload"
        
        manager = TableSheetManager(
            table_path=sample_md_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            creds_json=Path(creds_path),
            open_browser=False,
        )
        
        try:
            url = manager.sync_table_to_sheet()
            
            assert "https://docs.google.com/spreadsheets/d/" in url
            
        finally:
            # Cleanup
            from tabsheets.sheet_uploader import SheetUploader
            uploader = SheetUploader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=sample_md_file,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
                skip_prompt=True,
            )
            found = uploader.find_sheet_in_folder_by_name(test_folder_id, sheet_title)
            if found:
                cleanup.delete_file(found["id"])

    def test_sync_sheet_to_table_integration(
        self, drive_service, sheets_service, sample_md_file, test_folder_id, cleanup, tmp_path
    ):
        """Test full download workflow."""
        import os
        creds_path = os.environ.get("TABSHEETS_CREDENTIALS")
        if not creds_path:
            pytest.skip("TABSHEETS_CREDENTIALS not set")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_Manager_Download"
        
        # First upload
        from tabsheets.sheet_uploader import SheetUploader
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
            
            # Now use manager to download
            download_path = tmp_path / "manager_download.md"
            manager = TableSheetManager(
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
                creds_json=Path(creds_path),
            )
            
            result = manager.sync_sheet_to_table()
            
            assert download_path.exists()
            assert result == str(download_path)
            
            # Verify content
            original = extract_first_pipe_table(sample_md_file.read_text())
            downloaded = extract_first_pipe_table(download_path.read_text())
            assert original == downloaded
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)

    def test_overwrite_existing_sheet(
        self, drive_service, sheets_service, test_folder_id, cleanup, tmp_path
    ):
        """Test that uploading to an existing sheet overwrites it."""
        import os
        creds_path = os.environ.get("TABSHEETS_CREDENTIALS")
        if not creds_path:
            pytest.skip("TABSHEETS_CREDENTIALS not set")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_title = f"TEST_{timestamp}_Overwrite"
        
        # Create first file with initial data
        first_file = tmp_path / "first.md"
        first_file.write_text("""
| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |
""")
        
        # Upload first version
        from tabsheets.sheet_uploader import SheetUploader
        uploader = SheetUploader(
            drive=drive_service,
            sheets=sheets_service,
            table_path=first_file,
            sheet_title=sheet_title,
            drive_folder_id=test_folder_id,
            open_browser=False,
            skip_prompt=True,
        )
        
        try:
            url1 = uploader.upload()
            spreadsheet_id = uploader.spreadsheet_id
            
            # Create second file with different data
            second_file = tmp_path / "second.md"
            second_file.write_text("""
| Name | Value |
|------|-------|
| X    | 10    |
| Y    | 20    |
| Z    | 30    |
""")
            
            # Upload second version to same sheet title
            uploader2 = SheetUploader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=second_file,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
                open_browser=False,
                skip_prompt=True,
            )
            
            url2 = uploader2.upload()
            
            # Should be the same spreadsheet ID (overwritten, not new)
            assert uploader2.spreadsheet_id == spreadsheet_id
            
            # Now download and verify it has the second data
            download_path = tmp_path / "downloaded.md"
            from tabsheets.table_downloader import TableDownloader
            downloader = TableDownloader(
                drive=drive_service,
                sheets=sheets_service,
                table_path=download_path,
                sheet_title=sheet_title,
                drive_folder_id=test_folder_id,
            )
            
            downloader.download()
            
            # Verify it has the second data, not the first
            downloaded = extract_first_pipe_table(download_path.read_text())
            second_data = extract_first_pipe_table(second_file.read_text())
            
            assert downloaded == second_data
            assert len(downloaded) == 4  # Header + separator + 3 data rows
            
        finally:
            if uploader.spreadsheet_id:
                cleanup.delete_file(uploader.spreadsheet_id)
