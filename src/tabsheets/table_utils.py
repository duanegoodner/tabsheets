from __future__ import annotations

import csv
import re
from typing import List

SEP_RE = re.compile(r"^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|$")


def extract_first_pipe_table(md_text: str) -> List[List[str]]:
    """
    Extract the first Markdown pipe table (rows beginning and ending with '|').
    Assumes:
      - One logical pipe table
      - No multiline cells
      - Pipes '|' are used only as delimiters (not inside cell text)
    """
    lines = md_text.splitlines()
    table_lines: List[str] = []
    in_table = False

    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            in_table = True
            table_lines.append(s)
        else:
            if in_table:
                break

    if not table_lines:
        raise ValueError(
            "No Markdown pipe table found (lines that start and end with '|')."
        )

    rows: List[List[str]] = []
    for ln in table_lines:
        if SEP_RE.match(ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(cells)

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def extract_csv_table(csv_text: str) -> List[List[str]]:
    """Extract table from CSV text."""
    reader = csv.reader(csv_text.splitlines())
    rows = [list(row) for row in reader]

    if not rows:
        raise ValueError("No data found in CSV file.")

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def extract_tsv_table(tsv_text: str) -> List[List[str]]:
    """Extract table from TSV (tab-separated values) text."""
    reader = csv.reader(tsv_text.splitlines(), delimiter="\t")
    rows = [list(row) for row in reader]

    if not rows:
        raise ValueError("No data found in TSV file.")

    # Normalize width
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return rows


def a1_range_for_size(n_rows: int, n_cols: int) -> str:
    """Return an A1 range covering the given rows/cols, e.g. A1:AB123."""

    def col_to_a1(col_idx_0: int) -> str:
        # 0 -> A, 25 -> Z, 26 -> AA
        col = col_idx_0 + 1
        s = ""
        while col:
            col, rem = divmod(col - 1, 26)
            s = chr(65 + rem) + s
        return s

    end_col = col_to_a1(max(0, n_cols - 1))
    end_row = max(1, n_rows)
    return f"A1:{end_col}{end_row}"


def write_markdown_table(rows: List[List[str]]) -> str:
    """Convert table data to Markdown pipe table format."""
    if not rows:
        return ""
    
    # Calculate column widths
    n_cols = max(len(row) for row in rows) if rows else 0
    col_widths = [0] * n_cols
    
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
    
    lines = []
    for idx, row in enumerate(rows):
        # Pad row to full width
        padded_row = row + [""] * (n_cols - len(row))
        # Format cells with padding
        formatted_cells = [cell.ljust(col_widths[i]) for i, cell in enumerate(padded_row)]
        lines.append("| " + " | ".join(formatted_cells) + " |")
        
        # Add separator after header row
        if idx == 0:
            sep_cells = ["-" * col_widths[i] for i in range(n_cols)]
            lines.append("| " + " | ".join(sep_cells) + " |")
    
    return "\n".join(lines) + "\n"


def write_csv_table(rows: List[List[str]]) -> str:
    """Convert table data to CSV format."""
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()


def write_tsv_table(rows: List[List[str]]) -> str:
    """Convert table data to TSV format."""
    import io
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t")
    writer.writerows(rows)
    return output.getvalue()

