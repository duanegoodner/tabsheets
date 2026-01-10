"""Test utilities for cleaning up Google Drive resources."""
from __future__ import annotations

import warnings
from typing import Any


class DriveCleanup:
    """Helper for deleting test files from Google Drive."""

    def __init__(self, drive: Any):
        self.drive = drive

    def delete_file(self, file_id: str) -> None:
        """Delete a file from Google Drive by ID.
        
        For Shared Drive files, uses trash instead of delete since
        service accounts typically don't have delete permissions.
        Raises exception if cleanup fails.
        """
        # First get the file name for reporting
        try:
            file_info = self.drive.files().get(  # type: ignore
                fileId=file_id,
                fields="name",
                supportsAllDrives=True,
            ).execute()
            file_name = file_info.get("name", "Unknown")
        except Exception:
            file_name = "Unknown"
        
        # Trash the file
        self.drive.files().update(  # type: ignore
            fileId=file_id,
            body={"trashed": True},
            supportsAllDrives=True,
        ).execute()
        
        # Notify about successful cleanup
        print(f"\n✓ Cleaned up test file: {file_name} (moved to trash)")
        print(f"  File ID: {file_id}")

    def delete_files_by_prefix(self, folder_id: str, name_prefix: str) -> int:
        """Delete all files in a folder matching a name prefix.
        
        Returns the count of deleted files.
        """
        # Find all files with the prefix
        q = (
            f"'{folder_id}' in parents and "
            f"name contains '{name_prefix}' and "
            f"trashed = false"
        )

        params = {
            "q": q,
            "fields": "files(id, name)",
            "pageSize": 100,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "corpora": "allDrives",
        }

        resp = self.drive.files().list(**params).execute()  # type: ignore
        files = resp.get("files", [])

        # Delete each file
        for file in files:
            self.delete_file(file["id"])

        return len(files)
