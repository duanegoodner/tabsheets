"""Tests for table utility functions."""
import pytest
from pathlib import Path

from tabsheets.table_utils import (
    extract_first_pipe_table,
    extract_csv_table,
    extract_tsv_table,
    write_markdown_table,
    write_csv_table,
    write_tsv_table,
    a1_range_for_size,
)


class TestExtractMarkdownTable:
    """Test Markdown table extraction."""

    def test_extract_simple_table(self):
        """Test extracting a simple Markdown table."""
        md_text = """
# Header

| Col1 | Col2 |
|------|------|
| A    | B    |
| C    | D    |

Some text after.
"""
        result = extract_first_pipe_table(md_text)
        assert result == [
            ["Col1", "Col2"],
            ["A", "B"],
            ["C", "D"],
        ]

    def test_extract_table_with_alignment(self):
        """Test extracting table with alignment indicators."""
        md_text = """
| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
"""
        result = extract_first_pipe_table(md_text)
        assert result == [
            ["Left", "Center", "Right"],
            ["A", "B", "C"],
        ]

    def test_extract_no_table_raises_error(self):
        """Test that missing table raises error."""
        md_text = "Just some text without a table."
        
        with pytest.raises(ValueError, match="No Markdown pipe table found"):
            extract_first_pipe_table(md_text)


class TestExtractCSV:
    """Test CSV extraction."""

    def test_extract_simple_csv(self):
        """Test extracting simple CSV."""
        csv_text = "A,B,C\n1,2,3\n4,5,6"
        result = extract_csv_table(csv_text)
        assert result == [
            ["A", "B", "C"],
            ["1", "2", "3"],
            ["4", "5", "6"],
        ]

    def test_extract_empty_csv_raises_error(self):
        """Test that empty CSV raises error."""
        with pytest.raises(ValueError, match="No data found in CSV"):
            extract_csv_table("")


class TestExtractTSV:
    """Test TSV extraction."""

    def test_extract_simple_tsv(self):
        """Test extracting simple TSV."""
        tsv_text = "A\tB\tC\n1\t2\t3\n4\t5\t6"
        result = extract_tsv_table(tsv_text)
        assert result == [
            ["A", "B", "C"],
            ["1", "2", "3"],
            ["4", "5", "6"],
        ]


class TestWriteMarkdownTable:
    """Test Markdown table writing."""

    def test_write_simple_table(self):
        """Test writing a simple Markdown table."""
        data = [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
        ]
        result = write_markdown_table(data)
        
        assert "| Name  | Age |" in result
        assert "| Alice | 30  |" in result
        assert "| Bob   | 25  |" in result
        assert "| ----- | --- |" in result

    def test_write_empty_table(self):
        """Test writing empty table returns empty string."""
        result = write_markdown_table([])
        assert result == ""


class TestWriteCSV:
    """Test CSV writing."""

    def test_write_simple_csv(self):
        """Test writing simple CSV."""
        data = [
            ["A", "B", "C"],
            ["1", "2", "3"],
        ]
        result = write_csv_table(data)
        # Python's csv module uses \r\n (Windows line endings) by default on all platforms
        assert result == "A,B,C\r\n1,2,3\r\n"


class TestWriteTSV:
    """Test TSV writing."""

    def test_write_simple_tsv(self):
        """Test writing simple TSV."""
        data = [
            ["A", "B", "C"],
            ["1", "2", "3"],
        ]
        result = write_tsv_table(data)
        # Python's csv module uses \r\n (Windows line endings) by default on all platforms
        assert result == "A\tB\tC\r\n1\t2\t3\r\n"


class TestA1Range:
    """Test A1 range generation."""

    def test_single_cell(self):
        """Test A1 range for single cell."""
        assert a1_range_for_size(1, 1) == "A1:A1"

    def test_small_range(self):
        """Test A1 range for small table."""
        assert a1_range_for_size(10, 5) == "A1:E10"

    def test_wide_range(self):
        """Test A1 range extending beyond Z."""
        assert a1_range_for_size(5, 30) == "A1:AD5"

    def test_large_range(self):
        """Test A1 range for large table."""
        assert a1_range_for_size(100, 26) == "A1:Z100"
