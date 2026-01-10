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

