"""Debug script to inspect file permissions on Shared Drive."""
import os
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Get credentials
creds_path = os.environ.get("TABSHEETS_CREDENTIALS")
if not creds_path:
    print("Error: TABSHEETS_CREDENTIALS environment variable not set")
    sys.exit(1)

credentials = service_account.Credentials.from_service_account_file(
    creds_path,
    scopes=["https://www.googleapis.com/auth/drive"],
)

drive = build("drive", "v3", credentials=credentials)

# File ID from the test
file_id = "1XKFwqwT-GtYKzzVaooprdYpOX8Loh4dsntYxg2HfJUs"

print(f"\nInspecting file: {file_id}\n")

# Get file metadata with all fields
try:
    file_info = drive.files().get(
        fileId=file_id,
        fields="*",
        supportsAllDrives=True,
    ).execute()
    
    print("File found! Metadata:")
    print(f"  Name: {file_info.get('name')}")
    print(f"  ID: {file_info.get('id')}")
    print(f"  Owner: {file_info.get('owners', [{}])[0].get('emailAddress', 'Unknown')}")
    print(f"  Drive ID: {file_info.get('driveId', 'Not in Shared Drive')}")
    print(f"  Capabilities:")
    capabilities = file_info.get('capabilities', {})
    print(f"    Can delete: {capabilities.get('canDelete', False)}")
    print(f"    Can trash: {capabilities.get('canTrash', False)}")
    print(f"    Can remove children: {capabilities.get('canRemoveChildren', False)}")
    print(f"  Trashed: {file_info.get('trashed', False)}")
    print(f"  Parents: {file_info.get('parents', [])}")
    
    # Try to delete
    print("\n\nAttempting to delete file...")
    drive.files().delete(
        fileId=file_id,
        supportsAllDrives=True,
    ).execute()
    print("SUCCESS! File deleted.")
    
except Exception as e:
    print(f"Error: {e}")
