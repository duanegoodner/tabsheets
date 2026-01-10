# tabsheets

Sync tabular data files (Markdown tables, CSV, TSV) to Google Sheets using a service account.

## Features

- Supports multiple table formats: Markdown pipe tables, CSV, and TSV
- Uses Google service account authentication (no OAuth flow required)
- Automatically finds or creates spreadsheets by title in a specified Drive folder
- Prompts before overwriting existing spreadsheets
- Optional browser auto-open after sync
- Simple TOML-based configuration

## Installation

### From source (editable install)

```bash
# Clone the repository
git clone <your-repo-url>
cd tabsheets

# Create and activate conda environment
conda env create -f environment.yml
conda activate tabsheets

# Install the package in editable mode
pip install -e .
```

### Using pip

```bash
pip install tabsheets
```

## Prerequisites

### Google Service Account Setup

1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the Google Drive API and Google Sheets API for your project
3. Create a service account and download the JSON credentials file
4. Share your target Google Drive folder with the service account email address (found in the credentials JSON)

Store your credentials securely, e.g.:

```bash
mkdir -p ~/.config/gcloud
mv ~/Downloads/my-service-account-*.json ~/.config/gcloud/tabsheets-creds.json
chmod 600 ~/.config/gcloud/tabsheets-creds.json
```

## Usage

### Configuration File

Create a `config.toml` file:

```toml
[table_sheet_manager]
# Path to your table file (.md, .csv, or .tsv)
table_path = "/path/to/your/data/my_table.md"

# Google Drive folder ID where the spreadsheet will be created/found
# Find this in the folder URL: https://drive.google.com/drive/folders/<FOLDER_ID>
drive_folder_id = "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"

# Title for the Google Spreadsheet
# The script will search for a spreadsheet with this title in the folder above.
# If not found, it will create a new one.
sheet_title = "My Data Table"

# Open the spreadsheet in browser after syncing (optional, defaults to false)
open_browser = false
```

### Command Line

```bash
tabsheets --config config.toml --creds ~/.config/gcloud/tabsheets-creds.json
```

### Example

Given a Markdown table file `data/products.md`:

```markdown
| Product | Price | Stock |
|---------|-------|-------|
| Widget  | $10   | 50    |
| Gadget  | $25   | 30    |
```

And a `config.toml`:

```toml
[table_sheet_manager]
table_path = "data/products.md"
drive_folder_id = "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p"
sheet_title = "Product Inventory"
open_browser = true
```

Run:

```bash
tabsheets --config config.toml --creds ~/.config/gcloud/creds.json
```

The script will:
1. Read and parse `data/products.md`
2. Find or create a spreadsheet titled "Product Inventory" in the specified folder
3. Clear and update the sheet with the table data
4. Open the spreadsheet in your browser (since `open_browser = true`)
5. Print the spreadsheet URL

## Supported Table Formats

### Markdown (`.md`)

Pipe tables with optional alignment indicators:

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
```

### CSV (`.csv`)

Standard comma-separated values:

```csv
Column 1,Column 2
Value 1,Value 2
```

### TSV (`.tsv`)

Tab-separated values:

```tsv
Column 1	Column 2
Value 1	Value 2
```

## How It Works

1. **Authentication**: Uses Google service account credentials to access Drive and Sheets APIs
2. **File Discovery**: Searches for a spreadsheet with the configured title in the specified Drive folder
3. **User Confirmation**: If found, prompts before overwriting
4. **Table Parsing**: Extracts tabular data based on file extension (`.md`, `.csv`, `.tsv`)
5. **Sheet Update**: Clears a large range and writes the new data starting at cell A1
6. **Result**: Returns the spreadsheet URL


## License

MIT


